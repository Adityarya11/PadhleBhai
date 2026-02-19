#include <bits/stdc++.h>
using namespace std;

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(NULL), right(NULL) {}
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
    while (!q.empty() && i < n) {
        TreeNode* node = q.front();
        q.pop();

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

    queue<TreeNode*> level;
    level.push(root);
    while (!level.empty()) {
        int sz = level.size();
        for (int j = 0; j < sz; j++) {
            TreeNode* node = level.front();
            level.pop();
            cout << node->val << " ";
            if (node->left) level.push(node->left);
            if (node->right) level.push(node->right);
        }
        cout << "\n";
    }

    return 0;
}