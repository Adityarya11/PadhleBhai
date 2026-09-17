/*
 * Client-side search over the static index in search/.
 *
 * This is a port of scripts/search_cli.py and must stay in step with it: the
 * same tokeniser, the same shard resolution, the same BM25F scoring. When a
 * ranking looks wrong, compare the two - `python scripts/search_cli.py --explain
 * <query>` is the reference answer.
 *
 * Nothing is fetched until someone types. A query pulls meta.json and
 * manifest.json once, then only the term shards it touches and the text of the
 * handful of documents actually shown.
 */
(function () {
  'use strict';

  var ROOT = 'search';
  var SNIPPET_CHARS = 240;
  var RESULT_LIMIT = 12;
  var SNIPPET_RESULTS = 6;   // how many results get their text fetched
  var DEBOUNCE_MS = 120;

  // ---------------------------------------------------------------------
  // Index reader
  // ---------------------------------------------------------------------

  function Index() {
    this.ready = null;
    this.shardCache = new Map();
    this.textCache = new Map();
  }

  Index.prototype.load = function () {
    if (this.ready) return this.ready;
    var self = this;
    this.ready = Promise.all([
      fetch(ROOT + '/meta.json').then(function (r) { return r.json(); }),
      fetch(ROOT + '/manifest.json').then(function (r) { return r.json(); })
    ]).then(function (parts) {
      self.meta = parts[0];
      self.docs = parts[1];
      self.shardKeys = new Set(self.meta.shards);
      self.stopwords = new Set(self.meta.stopwords);
      return self;
    });
    return this.ready;
  };

  /* Mirrors tokens.tokenize(). Any change here needs the same change there. */
  Index.prototype.tokenize = function (text) {
    if (!text) return [];
    var out = [];
    var re = /[a-z0-9]+/g;
    var lowered = text.toLowerCase();
    var match;
    while ((match = re.exec(lowered)) !== null) {
      var token = match[0];
      if (token.length > this.meta.maxTokenLen) continue;
      if (this.stopwords.has(token)) continue;
      // A lone digit is a real query term here ("Lecture 5"); a lone letter
      // never is.
      if (token.length < this.meta.minTokenLen && !/^[0-9]$/.test(token)) continue;
      out.push(token);
    }
    return out;
  };

  /* Longest matching shard key wins. The floor is min(term.length, shardWidth),
     not shardWidth - otherwise a 1-character term resolves to nothing. */
  Index.prototype.shardFor = function (term) {
    var floor = Math.min(term.length, this.meta.shardWidth);
    for (var len = term.length; len >= floor; len--) {
      var key = term.slice(0, len);
      if (this.shardKeys.has(key)) return this.loadShard(key);
    }
    return Promise.resolve({});
  };

  Index.prototype.loadShard = function (key) {
    if (!this.shardCache.has(key)) {
      // Some shard keys collide with Windows device names (con, prn, aux...),
      // which git on Windows cannot check out. The build renames those files
      // and lists the exceptions in meta.json, so nothing here needs the list.
      var file = (this.meta.shardFiles && this.meta.shardFiles[key]) || key;
      this.shardCache.set(key, fetch(ROOT + '/terms/' + file + '.json')
        .then(function (r) { return r.ok ? r.json() : {}; })
        .catch(function () { return {}; }));
    }
    return this.shardCache.get(key);
  };

  Index.prototype.postings = function (term) {
    return this.shardFor(term).then(function (shard) {
      return shard[term] || [];
    });
  };

  Index.prototype.expandPrefix = function (prefix, limit) {
    return this.shardFor(prefix).then(function (shard) {
      var hits = [];
      for (var term in shard) {
        if (term.indexOf(prefix) === 0) hits.push(term);
      }
      hits.sort();
      return hits.slice(0, limit || 24);
    });
  };

  Index.prototype.docText = function (record, bucket) {
    var key = record.id + '-' + bucket;
    if (!this.textCache.has(key)) {
      this.textCache.set(key, fetch(ROOT + '/docs/' + key + '.json')
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; }));
    }
    return this.textCache.get(key);
  };

  // ---------------------------------------------------------------------
  // Scoring - BM25F, mirroring search_cli.search()
  // ---------------------------------------------------------------------

  function idf(total, df) {
    return Math.log(1 + (total - df + 0.5) / (df + 0.5));
  }

  Index.prototype.search = function (query, limit) {
    var self = this;
    var terms = this.tokenize(query);
    if (!terms.length) return Promise.resolve([]);

    var total = this.meta.docs;
    var k1 = this.meta.k1, b = this.meta.b;
    var avgdl = this.meta.avgdl || 1;
    var pathWeight = this.meta.pathWeight;

    // Only the last term is prefix-expanded, so as-you-type completes the word
    // being typed without every earlier word matching loosely too.
    var jobs = terms.map(function (term, position) {
      var isLast = position === terms.length - 1;
      var variants = (isLast && term.length >= 3)
        ? self.expandPrefix(term).then(function (v) { return v.length ? v : [term]; })
        : Promise.resolve([term]);
      return variants.then(function (list) {
        return Promise.all(list.map(function (variant) {
          return self.postings(variant).then(function (entries) {
            return { term: term, variant: variant, position: position, entries: entries };
          });
        }));
      });
    });

    return Promise.all(jobs).then(function (groups) {
      var bodyScore = new Map(), pathScore = new Map();
      var covered = new Map(), pathCovered = new Map();

      function mark(map, doc, position) {
        var set = map.get(doc);
        if (!set) { set = new Set(); map.set(doc, set); }
        set.add(position);
      }

      groups.forEach(function (group) {
        group.forEach(function (item) {
          var entries = item.entries;
          if (!entries.length) return;

          var bodyIdf = idf(total, entries.length);
          // The path field needs its own IDF: "5" is in almost every body but
          // in few filenames, so a shared IDF makes it worthless in both.
          var pathDf = 0;
          for (var i = 0; i < entries.length; i++) {
            if (entries[i].length > 2 && entries[i][2]) pathDf++;
          }
          var pathIdf = pathDf ? idf(total, pathDf) : 0;
          var damp = item.variant === item.term ? 1 : 0.35;

          for (var j = 0; j < entries.length; j++) {
            var entry = entries[j];
            var doc = entry[0], bodyTf = entry[1];
            var pathTf = entry.length > 2 ? entry[2] : 0;

            if (bodyTf > 0) {
              var dl = self.docs[doc].dl || 0;
              var norm = k1 * (1 - b + b * (dl / avgdl));
              bodyScore.set(doc, (bodyScore.get(doc) || 0) +
                bodyIdf * (bodyTf * (k1 + 1)) / (bodyTf + norm) * damp);
              mark(covered, doc, item.position);
            }
            if (pathTf > 0) {
              pathScore.set(doc, (pathScore.get(doc) || 0) +
                pathIdf * pathWeight * (pathTf * (k1 + 1)) / (pathTf + k1) * damp);
              mark(covered, doc, item.position);
              mark(pathCovered, doc, item.position);
            }
          }
        });
      });

      var scored = [];
      var seen = new Set();
      [bodyScore, pathScore].forEach(function (map) {
        map.forEach(function (_, doc) { seen.add(doc); });
      });

      seen.forEach(function (doc) {
        // A name match only counts fully when the whole query matches the name.
        var pathFraction = (pathCovered.get(doc) ? pathCovered.get(doc).size : 0) / terms.length;
        var score = (bodyScore.get(doc) || 0) + (pathScore.get(doc) || 0) * pathFraction;
        // Matching every word beats matching one common word loudly.
        var coverage = (covered.get(doc) ? covered.get(doc).size : 0) / terms.length;
        scored.push({ doc: self.docs[doc], score: score * Math.pow(coverage, 1.5) });
      });

      scored.sort(function (a, b2) { return b2.score - a.score; });
      return scored.slice(0, limit || RESULT_LIMIT);
    });
  };

  /* Which units of a document contain the query terms.
     Only bucket 0 by default: 92% of documents fit in one, and walking a
     29-bucket textbook to find a snippet turns a query into a 1 MB download. */
  Index.prototype.locate = function (record, terms, maxHits, maxBuckets) {
    var self = this;
    if (!record.buckets) return Promise.resolve({ hits: [], complete: true });

    var last = Math.min(record.buckets, maxBuckets || 1);
    var wanted = new Set(terms);
    var buckets = [];
    for (var i = 0; i < last; i++) buckets.push(i);

    return Promise.all(buckets.map(function (n) { return self.docText(record, n); }))
      .then(function (payloads) {
        var hits = [];
        for (var p = 0; p < payloads.length && hits.length < (maxHits || 2); p++) {
          var payload = payloads[p];
          if (!payload) continue;
          for (var u = 0; u < payload.units.length; u++) {
            var unitTerms = self.tokenize(payload.units[u]);
            var overlap = [];
            for (var t = 0; t < unitTerms.length; t++) {
              if (wanted.has(unitTerms[t]) && overlap.indexOf(unitTerms[t]) < 0) {
                overlap.push(unitTerms[t]);
              }
            }
            if (!overlap.length) continue;
            hits.push({
              unit: payload.from + u,
              terms: overlap,
              snippet: makeSnippet(payload.units[u], overlap)
            });
            if (hits.length >= (maxHits || 2)) break;
          }
        }
        return { hits: hits, complete: last >= record.buckets };
      });
  };

  function makeSnippet(text, terms) {
    var lowered = text.toLowerCase();
    var position = -1;
    terms.forEach(function (term) {
      var found = lowered.indexOf(term);
      if (found >= 0 && (position < 0 || found < position)) position = found;
    });
    if (position < 0) position = 0;
    var start = Math.max(0, position - Math.floor(SNIPPET_CHARS / 3));
    var excerpt = text.slice(start, start + SNIPPET_CHARS)
      .replace(/\s+/g, ' ').trim();
    return (start > 0 ? '…' : '') + excerpt + '…';
  }

  // ---------------------------------------------------------------------
  // fzf-style fuzzy matching, for the @ picker
  // ---------------------------------------------------------------------

  /* Subsequence match with a bonus for consecutive characters and for matches
     at word boundaries, so "dpmc" finds "DP_matrix_chain". Returns -1 for no
     match. */
  function fuzzyScore(needle, haystack) {
    var hay = haystack.toLowerCase();
    var score = 0, index = 0, previous = -2, run = 0;
    for (var i = 0; i < needle.length; i++) {
      index = hay.indexOf(needle[i], index);
      if (index < 0) return -1;
      if (index === previous + 1) { run++; score += 6 + run * 2; }
      else { run = 0; score += 1; }
      var before = index > 0 ? hay[index - 1] : '/';
      if (before === '/' || before === '_' || before === '-' || before === ' ') score += 8;
      previous = index;
      index++;
    }
    // Prefer shorter names when scores are otherwise close.
    return score - haystack.length * 0.05;
  }

  // ---------------------------------------------------------------------
  // UI
  // ---------------------------------------------------------------------

  function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function highlight(text, terms) {
    var escaped = escapeHtml(text);
    terms.forEach(function (term) {
      var safe = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      escaped = escaped.replace(new RegExp('(' + safe + ')', 'gi'), '<mark>$1</mark>');
    });
    return escaped;
  }

  function fileUrl(index, record, unit) {
    var encoded = record.path.split('/').map(encodeURIComponent).join('/');
    // Pages serves an LFS file as its 133-byte pointer, so those have to come
    // from the media host or the link opens a text file instead of the PDF.
    var url = record.lfs && index.meta.lfsBase
      ? index.meta.lfsBase + encoded
      : encoded;
    // PDF viewers honour #page=N, which turns a hit into a direct jump.
    if (unit != null && record.ext === '.pdf') url += '#page=' + (unit + 1);
    return url;
  }

  function crumbs(record) {
    var parts = record.path.split('/');
    parts.pop();
    return parts.join(' › ');
  }

  function unitLabel(record, unit) {
    return record.unit + ' ' + (unit + 1);
  }

  function App(index) {
    this.index = index;
    this.input = document.getElementById('q');
    this.panel = document.getElementById('search-panel');
    this.results = document.getElementById('search-results');
    this.status = document.getElementById('search-status');
    this.tree = document.getElementById('file-tree');
    this.toolbar = document.querySelector('.toolbar');
    this.timer = null;
    this.sequence = 0;
    this.bind();
  }

  App.prototype.bind = function () {
    var self = this;
    this.input.addEventListener('input', function () {
      clearTimeout(self.timer);
      self.timer = setTimeout(function () { self.run(); }, DEBOUNCE_MS);
    });
    this.input.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { self.input.value = ''; self.run(); }
    });
    // "/" focuses the box, the way every search-first tool behaves.
    document.addEventListener('keydown', function (event) {
      if (event.key === '/' && document.activeElement !== self.input) {
        event.preventDefault();
        self.input.focus();
      }
    });
    this.results.addEventListener('click', function (event) {
      var pick = event.target.closest('[data-pick]');
      if (pick) {
        self.input.value = '@' + pick.getAttribute('data-pick');
        self.run();
        return;
      }
      var more = event.target.closest('[data-deep]');
      if (more) self.deepen(more.getAttribute('data-deep'), more);
    });
  };

  App.prototype.setActive = function (active) {
    this.panel.hidden = !active;
    if (this.tree) this.tree.hidden = active;
    if (this.toolbar) this.toolbar.hidden = active;
  };

  App.prototype.run = function () {
    var raw = this.input.value.trim();
    var self = this;
    var token = ++this.sequence;

    if (!raw) { this.setActive(false); this.results.innerHTML = ''; this.status.textContent = ''; return; }
    this.setActive(true);

    return this.index.load().then(function () {
      if (token !== self.sequence) return;    // a newer keystroke won
      if (raw.charAt(0) === '@') return self.renderPicker(raw.slice(1), token);
      return self.renderResults(raw, token);
    });
  };

  // --- @ picker ---------------------------------------------------------

  App.prototype.renderPicker = function (needle, token) {
    var self = this;
    var query = needle.toLowerCase().replace(/\s+/g, '');
    var docs = this.index.docs;
    var matches = [];

    if (!query) {
      matches = docs.slice(0, 40).map(function (d) { return { doc: d, score: 0 }; });
    } else {
      for (var i = 0; i < docs.length; i++) {
        var score = fuzzyScore(query, docs[i].path);
        if (score > 0) matches.push({ doc: docs[i], score: score });
      }
      matches.sort(function (a, b) { return b.score - a.score; });
      matches = matches.slice(0, 40);
    }

    if (token !== this.sequence) return;
    this.status.textContent = matches.length
      ? matches.length + ' document' + (matches.length === 1 ? '' : 's') + ' — pick one for its card'
      : 'No document matches that name.';

    // An exact single choice goes straight to the card.
    if (matches.length === 1) return this.renderCard(matches[0].doc, token);

    this.results.innerHTML = matches.map(function (m) {
      var d = m.doc;
      return '<button class="pick" data-pick="' + escapeHtml(d.path) + '">' +
        '<span class="pick-name">' + escapeHtml(d.name) + '</span>' +
        '<span class="pick-path">' + escapeHtml(crumbs(d)) + '</span>' +
        '</button>';
    }).join('');
  };

  App.prototype.renderCard = function (record, token) {
    var self = this;
    var preview = record.buckets
      ? this.index.docText(record, 0).then(function (payload) {
          if (!payload || !payload.units.length) return '';
          return payload.units.find(function (u) { return u.trim(); }) || '';
        })
      : Promise.resolve('');

    return preview.then(function (text) {
      if (token !== self.sequence) return;
      var facts = [];
      if (record.sem) facts.push(record.sem);
      if (record.subject) facts.push(record.subject);
      facts.push(record.category);
      if (record.pages) facts.push(record.pages + ' ' + record.unit + 's');
      facts.push(formatSize(record.size));

      var html = '<article class="card">' +
        '<h2>' + escapeHtml(record.title) + '</h2>' +
        '<div class="card-path">' + escapeHtml(record.path) + '</div>' +
        '<div class="card-facts">' + facts.map(escapeHtml).join(' · ') + '</div>';

      if (record.keywords && record.keywords.length) {
        html += '<div class="card-keywords">' + record.keywords.map(function (k) {
          return '<span class="kw">' + escapeHtml(k) + '</span>';
        }).join('') + '</div>';
      }
      if (!record.text) {
        html += '<p class="card-note">No text layer in this file — it is a scan, ' +
          'so it is findable by name but its contents are not searchable yet.</p>';
      }
      if (text) {
        html += '<p class="card-preview">' + escapeHtml(text.slice(0, 420).replace(/\s+/g, ' ')) + '…</p>';
      }
      if (record.also_at && record.also_at.length) {
        html += '<div class="card-note">Also filed at: ' +
          record.also_at.map(escapeHtml).join(', ') + '</div>';
      }
      html += '<div class="card-actions">' +
        '<a class="btn btn-view" href="' + fileUrl(self.index, record) + '" target="_blank" rel="noopener">Open</a>' +
        '<a class="btn btn-dl" href="' + fileUrl(self.index, record) + '" download>Download</a>' +
        '</div></article>';

      self.results.innerHTML = html;
      self.status.textContent = 'Document card — read it yourself, that is the point.';
    });
  };

  // --- results ----------------------------------------------------------

  App.prototype.renderResults = function (query, token) {
    var self = this;
    var terms = this.index.tokenize(query);

    return this.index.search(query, RESULT_LIMIT).then(function (results) {
      if (token !== self.sequence) return;
      if (!results.length) {
        self.status.textContent = 'Nothing found for “' + query + '”.';
        self.results.innerHTML = '<p class="empty">Try fewer words, or browse the tree below. ' +
          'Scanned handwritten notes are findable by name only.</p>';
        self.setActive(true);
        if (self.tree) self.tree.hidden = false;
        return;
      }

      self.status.textContent = results.length + ' result' +
        (results.length === 1 ? '' : 's') + ' — type @ to look up a document by name';
      self.results.innerHTML = results.map(function (r) {
        return self.resultHtml(r.doc, terms);
      }).join('');

      // Snippets only for the top few, so a query never pulls the whole corpus.
      results.slice(0, SNIPPET_RESULTS).forEach(function (r) {
        self.index.locate(r.doc, terms, 2, 1).then(function (found) {
          if (token !== self.sequence) return;
          var slot = self.results.querySelector('[data-hits="' + r.doc.id + '"]');
          if (!slot) return;
          if (found.hits.length) {
            slot.innerHTML = found.hits.map(function (hit) {
              return '<a class="hit" href="' + fileUrl(self.index, r.doc, hit.unit) + '" target="_blank" rel="noopener">' +
                '<span class="hit-unit">' + escapeHtml(unitLabel(r.doc, hit.unit)) + '</span>' +
                '<span class="hit-text">' + highlight(hit.snippet, hit.terms) + '</span></a>';
            }).join('');
          } else if (!found.complete) {
            slot.innerHTML = '<button class="hit-more" data-deep="' + r.doc.id + '">' +
              'Matches further inside this document — search deeper</button>';
          }
        });
      });
    });
  };

  App.prototype.resultHtml = function (record, terms) {
    var self = this;
    var facts = [];
    if (record.sem) facts.push(record.sem);
    if (record.subject) facts.push(record.subject);
    facts.push(record.category);
    if (record.pages) facts.push(record.pages + ' ' + record.unit + 's');

    var note = record.text ? '' :
      '<span class="flag" title="Scanned document with no text layer">name match only</span>';

    return '<article class="result">' +
      '<div class="result-head">' +
        '<a class="result-title" href="' + fileUrl(self.index, record) + '" target="_blank" rel="noopener">' +
          escapeHtml(record.title) + '</a>' + note +
      '</div>' +
      '<div class="result-path">' + escapeHtml(crumbs(record)) + '</div>' +
      '<div class="result-facts">' + facts.map(escapeHtml).join(' · ') + '</div>' +
      '<div class="result-hits" data-hits="' + escapeHtml(record.id) + '"></div>' +
      '<div class="result-actions">' +
        '<button class="btn btn-ghost" data-pick="' + escapeHtml(record.path) + '">Card</button>' +
        '<a class="btn btn-dl" href="' + fileUrl(self.index, record) + '" download>Download</a>' +
      '</div></article>';
  };

  /* Scan every bucket of one document, on request. This is the escape hatch for
     big textbooks, where bucket 0 holds only the first few dozen pages. */
  App.prototype.deepen = function (docId, button) {
    var self = this;
    var record = this.index.docs.find(function (d) { return d.id === docId; });
    if (!record) return;
    var terms = this.index.tokenize(this.input.value);
    button.textContent = 'Searching the whole document…';
    button.disabled = true;

    this.index.locate(record, terms, 3, record.buckets).then(function (found) {
      var slot = self.results.querySelector('[data-hits="' + docId + '"]');
      if (!slot) return;
      slot.innerHTML = found.hits.length
        ? found.hits.map(function (hit) {
            return '<a class="hit" href="' + fileUrl(self.index, record, hit.unit) + '" target="_blank" rel="noopener">' +
              '<span class="hit-unit">' + escapeHtml(unitLabel(record, hit.unit)) + '</span>' +
              '<span class="hit-text">' + highlight(hit.snippet, hit.terms) + '</span></a>';
          }).join('')
        : '<span class="hit-none">The words rank this document highly but appear in no single page together.</span>';
    });
  };

  function formatSize(bytes) {
    var units = ['B', 'KB', 'MB', 'GB'];
    var value = bytes || 0, i = 0;
    while (value >= 1024 && i < units.length - 1) { value /= 1024; i++; }
    return value.toFixed(value < 10 && i > 0 ? 1 : 0) + ' ' + units[i];
  }

  // ---------------------------------------------------------------------

  // Exposed so the engine can be exercised without a browser - see
  // scripts/check_parity.js, which runs the same queries through this code and
  // through search_cli.py and asserts the rankings match.
  var api = { Index: Index, fuzzyScore: fuzzyScore, makeSnippet: makeSnippet };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.PadhleSearch = api;

  if (typeof document === 'undefined') return;

  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('q')) return;
    var index = new Index();
    var app = new App(index);
    // Warm the manifest on first focus so the first keystroke feels instant.
    app.input.addEventListener('focus', function () { index.load(); }, { once: true });
    // Support deep links like index.html?q=deadlock
    var initial = new URLSearchParams(location.search).get('q');
    if (initial) { app.input.value = initial; app.run(); }
  });
})();
