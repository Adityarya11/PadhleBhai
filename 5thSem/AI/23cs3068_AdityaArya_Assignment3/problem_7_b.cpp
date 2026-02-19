#include <bits/stdc++.h>
using namespace std;

double gini(const vector<int>& labels) {
    if (labels.empty()) return 0.0;
    int cnt0 = 0, cnt1 = 0;
    for (int y : labels) {
        if (y == 0) cnt0++;
        else cnt1++;
    }
    double p0 = (double)cnt0 / labels.size();
    double p1 = (double)cnt1 / labels.size();
    return 1.0 - p0 * p0 - p1 * p1;
}

double weightedGini(const vector<pair<int,int>>& data, int t) {
    vector<int> left, right;
    for (auto &p : data) {
        if (p.first <= t) left.push_back(p.second);
        else right.push_back(p.second);
    }
    double n = data.size();
    return (left.size() / n) * gini(left) + (right.size() / n) * gini(right);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<pair<int,int>> data(n);
    for (int i = 0; i < n; i++) cin >> data[i].first >> data[i].second;

    int t1, t2;
    cin >> t1 >> t2;

    double g1 = weightedGini(data, t1);
    double g2 = weightedGini(data, t2);

    if (g1 < g2 || fabs(g1 - g2) < 1e-9) 
        cout << t1 << " " << fixed << setprecision(6) << g1;
    else 
        cout << t2 << " " << fixed << setprecision(6) << g2;

    return 0;
}