#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    int count0 = 0, count1 = 0;

    for (int i = 0; i < n; i++) {
        int y;
        cin >> y;
        if (y == 0) count0++;
        else count1++;
    }

    double entropy = 0.0;
    if (count0 > 0) {
        double p0 = (double)count0 / n;
        entropy -= p0 * log2(p0);
    }
    if (count1 > 0) {
        double p1 = (double)count1 / n;
        entropy -= p1 * log2(p1);
    }

    cout << fixed << setprecision(6) << entropy << "\n";
    return 0;
}