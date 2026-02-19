#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> x(n);
    for (int i = 0; i < n; i++) cin >> x[i];
    int t, s;
    cin >> t >> s;

    for (int i = 0; i < n; i++) {
        int pred = (s * (x[i] - t) <= 0) ? 1 : -1;
        cout << pred << "\n";
    }
    return 0;
}