#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    int cnt0 = 0, cnt1 = 0;
    for (int i = 0; i < n; i++) {
        int x; cin >> x;
        if (x == 0) cnt0++;
        else cnt1++;
    }
    if (cnt1 > cnt0) cout << 1;
    else cout << 0;
    return 0;
}