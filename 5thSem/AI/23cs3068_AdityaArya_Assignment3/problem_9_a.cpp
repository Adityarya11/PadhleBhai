#include <bits/stdc++.h>
using namespace std;

struct TreeNode {
    int val;
    TreeNode *left, *right;
    TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> arr(n);
    for (int i = 0; i < n; i++) cin >> arr[i];
    if (n == 0 || arr[0] == -1) return 0;

    TreeNode* root = new TreeNode(arr[0]);
    queue<TreeNode*> q;
    q.push(root);
    int i = 1;
    while (i < n) {
        TreeNode* node = q.front(); q.pop();
        if (i < n && arr[i] != -1) {
            node->left = new TreeNode(arr[i]);
            q.push(node->left);
        }
        i++;
        if (i < n && arr[i] != -1) {
            node->right = new TreeNode(arr[i]);
            q.push(node->right);
        }
        i++;
    }

    queue<TreeNode*> bfs;
    bfs.push(root);
    while (!bfs.empty()) {
        int sz = bfs.size();
        TreeNode* last = nullptr;
        for (int j = 0; j < sz; j++) {
            TreeNode* node = bfs.front(); bfs.pop();
            last = node;
            if (node->left) bfs.push(node->left);
            if (node->right) bfs.push(node->right);
        }
        cout << last->val << "\n";
    }

    return 0;
}