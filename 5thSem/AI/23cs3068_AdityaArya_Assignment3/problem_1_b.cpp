#include <bits/stdc++.h>
using namespace std;

struct Point {
    double x;
    int y;
};

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
    vector<Point> data(n);
    for (int i = 0; i < n; i++) cin >> data[i].x >> data[i].y;

    sort(data.begin(), data.end(), [](const Point &a, const Point &b) {
        return a.x < b.x;
    });

    int total0 = 0, total1 = 0;
    for (auto &p : data) {
        if (p.y == 0) total0++;
        else total1++;
    }

    int left0 = 0, left1 = 0;
    double bestThreshold = 0.0, bestGini = 1e9;

    for (int i = 0; i < n - 1; i++) {
        if (data[i].y == 0) left0++;
        else left1++;

        double threshold = (data[i].x + data[i + 1].x) / 2.0;

        int right0 = total0 - left0;
        int right1 = total1 - left1;

        int leftSize = left0 + left1;
        int rightSize = right0 + right1;

        double giniLeft = gini(left0, left1);
        double giniRight = gini(right0, right1);

        double weighted = (double)leftSize / n * giniLeft +
                          (double)rightSize / n * giniRight;

        if (weighted < bestGini) {
            bestGini = weighted;
            bestThreshold = threshold;
        }
    }

    cout << fixed << setprecision(6) << bestThreshold << " " << bestGini << "\n";
    return 0;
}