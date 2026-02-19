#include <bits/stdc++.h>
using namespace std;

struct SparseTable {
    int n, K;
    vector<vector<int>> st;
    vector<int> log;

    SparseTable(const vector<int>& arr) {
        n = arr.size();
        K = log2(n) + 1;
        st.assign(n, vector<int>(K));
        log.assign(n + 1, 0);
        for (int i = 2; i <= n; i++) log[i] = log[i/2] + 1;
        for (int i = 0; i < n; i++) st[i][0] = arr[i];
        for (int j = 1; j < K; j++) {
            for (int i = 0; i + (1 << j) <= n; i++) {
                st[i][j] = min(st[i][j-1], st[i + (1 << (j-1))][j-1]);
            }
        }
    }

    int query(int L, int R) {
        int j = log[R - L + 1];
        return min(st[L][j], st[R - (1 << j) + 1][j]);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> arr(n);
    for (int i = 0; i < n; i++) cin >> arr[i];
    SparseTable st(arr);
    int q;
    cin >> q;
    while (q--) {
        int l, r;
        cin >> l >> r;
        l--, r--;
        cout << st.query(l, r) << "\n";
    }
    return 0;
}