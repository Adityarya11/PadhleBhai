#include <bits/stdc++.h>
using namespace std;

double gini(int c0, int c1) {
    int total = c0 + c1;
    if (total == 0) return 0.0;
    double p0 = (double)c0 / total;
    double p1 = (double)c1 / total;
    return 1.0 - (p0 * p0 + p1 * p1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<pair<int,int>> data(n);
    for (int i = 0; i < n; i++) cin >> data[i].first >> data[i].second;

    int t;
    cin >> t;

    int left0 = 0, left1 = 0, right0 = 0, right1 = 0;
    for (auto &p : data) {
        if (p.first <= t) {
            if (p.second == 0) left0++;
            else left1++;
        } else {
            if (p.second == 0) right0++;
            else right1++;
        }
    }

    int leftSize = left0 + left1;
    int rightSize = right0 + right1;
    int total = leftSize + rightSize;

    double giniLeft = gini(left0, left1);
    double giniRight = gini(right0, right1);

    double weighted = (double)leftSize / total * giniLeft + (double)rightSize / total * giniRight;

    cout << fixed << setprecision(6) << weighted << "\n";
    return 0;
}