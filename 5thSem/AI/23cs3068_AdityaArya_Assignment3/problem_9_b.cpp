#include <bits/stdc++.h>
using namespace std;

double entropy(const vector<int>& labels) {
    if (labels.empty()) return 0.0;
    int cnt0 = 0, cnt1 = 0;
    for (int y : labels) (y == 0 ? cnt0 : cnt1)++;
    double n = labels.size();
    double p0 = cnt0 / n, p1 = cnt1 / n;
    double h = 0.0;
    if (p0 > 0) h -= p0 * log2(p0);
    if (p1 > 0) h -= p1 * log2(p1);
    return h;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, d;
    cin >> n >> d;
    vector<vector<int>> features(n, vector<int>(d));
    vector<int> labels(n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < d; j++) cin >> features[i][j];
        cin >> labels[i];
    }

    double baseEntropy = entropy(labels);
    int bestFeature = 0;
    double bestIG = -1;

    for (int j = 0; j < d; j++) {
        vector<int> left, right;
        for (int i = 0; i < n; i++) {
            if (features[i][j] == 0) left.push_back(labels[i]);
            else right.push_back(labels[i]);
        }
        double wLeft = (double)left.size() / n;
        double wRight = (double)right.size() / n;
        double condEntropy = wLeft * entropy(left) + wRight * entropy(right);
        double ig = baseEntropy - condEntropy;
        if (ig > bestIG) {
            bestIG = ig;
            bestFeature = j;
        }
    }

    cout << bestFeature << " " << fixed << setprecision(6) << bestIG << "\n";
    return 0;
}