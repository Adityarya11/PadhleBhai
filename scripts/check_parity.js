/*
 * Verify that assets/search.js ranks exactly the way scripts/search_cli.py does.
 *
 *     node scripts/check_parity.js
 *
 * Two implementations of the same scoring drift apart silently - a tweak lands
 * in one and not the other, and the site quietly stops matching the reference.
 * This runs a fixed set of queries through the browser engine (with fetch
 * pointed at the local search/ directory) and writes the rankings as JSON;
 * search_cli.py is run over the same queries and the two are compared.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

// Stand in for the browser's fetch, reading straight off disk.
global.fetch = async function (url) {
  const file = path.join(ROOT, url);
  try {
    const data = await fs.promises.readFile(file, 'utf8');
    return { ok: true, json: async () => JSON.parse(data) };
  } catch (err) {
    return { ok: false, json: async () => null };
  }
};

const { Index } = require('../assets/search.js');

const QUERIES = [
  'matrix chain',
  'dynamic programming',
  'deadlock',
  'congestion control',
  'externalities',
  'lecture 5',
  'unit 3',
  'kruskal',
  'transformer attention',
  'normalization database',
  'dijkstra',
  'lab 2',
];

(async function main() {
  const index = new Index();
  await index.load();

  const out = {};
  for (const query of QUERIES) {
    const results = await index.search(query, 5);
    out[query] = results.map((r) => ({
      path: r.doc.path,
      score: Number(r.score.toFixed(4)),
    }));
  }

  // Tokeniser parity is checked separately: it is the part most likely to drift,
  // and a mismatch there explains every downstream difference.
  const TOKEN_SAMPLES = [
    'Dynamic Programming: matrix-chain multiplication',
    'Lecture 5',
    'IPv4 fragmentation & MTU',
    '00111110011011010000000000000000 binary32',
    'a an the of 7 x',
    'Unit-3 SCC Mid_Sem',
  ];
  out.__tokens__ = {};
  for (const sample of TOKEN_SAMPLES) {
    out.__tokens__[sample] = index.tokenize(sample);
  }

  process.stdout.write(JSON.stringify(out, null, 1));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
