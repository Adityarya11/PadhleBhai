#include <bits/stdc++.h>
using namespace std;

struct Split {
    int feature;
    double threshold;
    double gini;
    bool valid;
};

double giniImpurity(const vector<int>& labels) {
    if (labels.empty()) return 0.0;
    int cnt0 = 0, cnt1 = 0;
    for (int y : labels) (y == 0 ? cnt0 : cnt1)++;
    double n = labels.size();
    double p0 = cnt0 / n, p1 = cnt1 / n;
    return 1.0 - p0 * p0 - p1 * p1;
}

Split bestSplit(const vector<vector<double>>& X, const vector<int>& y, const vector<int>& idx) {
    int n = idx.size(), d = X[0].size();
    Split best{-1, 0.0, 1e9, false};
    for (int f = 0; f < d; f++) {
        vector<pair<double,int>> vals;
        for (int i : idx) vals.push_back({X[i][f], y[i]});
        sort(vals.begin(), vals.end());
        for (int j = 1; j < n; j++) {
            if (vals[j-1].first == vals[j].first) continue;
            double thr = (vals[j-1].first + vals[j].first) / 2.0;
            vector<int> left, right;
            for (auto &p : vals) {
                if (p.first <= thr) left.push_back(p.second);
                else right.push_back(p.second);
            }
            double g = (double)left.size()/n * giniImpurity(left)
                     + (double)right.size()/n * giniImpurity(right);
            if (g < best.gini) {
                best = {f, thr, g, true};
            }
        }
    }
    return best;
}

int majorityClass(const vector<int>& labels) {
    int cnt0 = 0, cnt1 = 0;
    for (int y : labels) (y == 0 ? cnt0 : cnt1)++;
    return (cnt1 > cnt0 ? 1 : 0);
}

struct Node {
    bool isLeaf;
    int feature;
    double threshold;
    int prediction;
    Node* left;
    Node* right;
    Node(): isLeaf(true), feature(-1), threshold(0), prediction(0), left(nullptr), right(nullptr) {}
};

Node* buildTree(const vector<vector<double>>& X, const vector<int>& y, const vector<int>& idx, int depth) {
    Node* node = new Node();
    if (depth == 2 || idx.empty()) {
        node->isLeaf = true;
        vector<int> labels;
        for (int i : idx) labels.push_back(y[i]);
        node->prediction = majorityClass(labels);
        return node;
    }
    Split sp = bestSplit(X, y, idx);
    if (!sp.valid) {
        node->isLeaf = true;
        vector<int> labels;
        for (int i : idx) labels.push_back(y[i]);
        node->prediction = majorityClass(labels);
        return node;
    }
    node->isLeaf = false;
    node->feature = sp.feature;
    node->threshold = sp.threshold;
    vector<int> leftIdx, rightIdx;
    for (int i : idx) {
        if (X[i][sp.feature] <= sp.threshold) leftIdx.push_back(i);
        else rightIdx.push_back(i);
    }
    node->left = buildTree(X, y, leftIdx, depth+1);
    node->right = buildTree(X, y, rightIdx, depth+1);
    return node;
}

int predict(Node* root, const vector<double>& x) {
    Node* node = root;
    while (!node->isLeaf) {
        if (x[node->feature] <= node->threshold) node = node->left;
        else node = node->right;
    }
    return node->prediction;
}

void printTree(Node* node, int depth=0) {
    if (node->isLeaf) {
        cout << string(depth*2, ' ') << "Leaf: predict=" << node->prediction << "\n";
    } else {
        cout << string(depth*2, ' ') << "Split: feature=" << node->feature 
             << " threshold=" << node->threshold << "\n";
        printTree(node->left, depth+1);
        printTree(node->right, depth+1);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, d;
    cin >> n >> d;
    vector<vector<double>> X(n, vector<double>(d));
    vector<int> y(n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < d; j++) cin >> X[i][j];
        cin >> y[i];
    }

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    Node* root = buildTree(X, y, idx, 0);

    printTree(root);

    int correct = 0;
    for (int i = 0; i < n; i++) {
        if (predict(root, X[i]) == y[i]) correct++;
    }
    double acc = (double)correct / n;
    cout << "Accuracy: " << fixed << setprecision(6) << acc << "\n";
    return 0;
}