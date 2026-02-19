#include <bits/stdc++.h>
using namespace std;

double entropy(const vector<long long>& counts) {
    long long total = 0;
    for (auto c : counts) total += c;
    if (total == 0) return 0.0;
    double H = 0.0;
    for (auto c : counts) {
        if (c == 0) continue;
        double p = (double)c / total;
        H -= p * (log(p) / log(2.0));
    }
    return H;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int C, K;
    cin >> C >> K;

    vector<vector<long long>> cat(K, vector<long long>(C));
    vector<long long> parent(C, 0);
    vector<long long> catTotals(K, 0);
    long long N = 0;

    for (int k = 0; k < K; ++k) {
        for (int c = 0; c < C; ++c) {
            cin >> cat[k][c];
            parent[c] += cat[k][c];
            catTotals[k] += cat[k][c];
        }
        N += catTotals[k];
    }

    double H_parent = entropy(parent);
    double weighted_child_entropy = 0.0;
    for (int k = 0; k < K; ++k) {
        if (catTotals[k] == 0) continue;
        double weight = (double)catTotals[k] / N;
        weighted_child_entropy += weight * entropy(cat[k]);
    }

    double info_gain = H_parent - weighted_child_entropy;
    cout << fixed << setprecision(6) << info_gain << "\n";
    return 0;
}