#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long target;
    cin >> n >> target;

    vector<long long> arr(n);
    for (int i = 0; i < n; i++) cin >> arr[i];

    int l = 0, r = n - 1;
    while (l < r) {
        long long sum = arr[l] + arr[r];
        if (sum == target) {
            cout << l + 1 << " " << r + 1 << "\n";
            return 0;
        }
        if (sum < target) l++;
        else r--;
    }

    cout << "-1 -1\n";
    return 0;
}