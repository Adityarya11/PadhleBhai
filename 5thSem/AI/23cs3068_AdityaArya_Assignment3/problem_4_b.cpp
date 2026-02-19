#include <bits/stdc++.h>
using namespace std;

struct Point {
    double x, y;
};

double variance(int count, double sumY, double sumY2) {
    if (count == 0) return 0.0;
    double mean = sumY / count;
    return sumY2 / count - mean * mean;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<Point> data(n);
    for (int i = 0; i < n; i++) cin >> data[i].x >> data[i].y;

    sort(data.begin(), data.end(), [](auto &a, auto &b) {
        return a.x < b.x;
    });

    double totalSum = 0, totalSumSq = 0;
    for (auto &p : data) {
        totalSum += p.y;
        totalSumSq += p.y * p.y;
    }

    double totalVar = variance(n, totalSum, totalSumSq);

    double leftSum = 0, leftSumSq = 0;
    int leftCount = 0;

    double bestThreshold = 0.0, bestReduction = -1e18;

    for (int i = 0; i < n - 1; i++) {
        leftSum += data[i].y;
        leftSumSq += data[i].y * data[i].y;
        leftCount++;

        double rightSum = totalSum - leftSum;
        double rightSumSq = totalSumSq - leftSumSq;
        int rightCount = n - leftCount;

        double varLeft = variance(leftCount, leftSum, leftSumSq);
        double varRight = variance(rightCount, rightSum, rightSumSq);

        double weighted = (double)leftCount / n * varLeft +
                          (double)rightCount / n * varRight;

        double reduction = totalVar - weighted;

        double threshold = (data[i].x + data[i + 1].x) / 2.0;

        if (reduction > bestReduction) {
            bestReduction = reduction;
            bestThreshold = threshold;
        }
    }

    cout << fixed << setprecision(6) << bestThreshold << " " << bestReduction << "\n";
    return 0;
}