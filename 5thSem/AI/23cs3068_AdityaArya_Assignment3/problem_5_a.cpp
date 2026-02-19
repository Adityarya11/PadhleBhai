#include <bits/stdc++.h>
using namespace std;

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(NULL), right(NULL) {}
};

TreeNode* buildTree(vector<int>& preorder, int preStart, int preEnd,
                    vector<int>& inorder, int inStart, int inEnd,
                    unordered_map<int,int>& inIndex) {
    if (preStart > preEnd || inStart > inEnd) return NULL;

    int rootVal = preorder[preStart];
    TreeNode* root = new TreeNode(rootVal);

    int idx = inIndex[rootVal];
    int leftSize = idx - inStart;

    root->left = buildTree(preorder, preStart + 1, preStart + leftSize,
                           inorder, inStart, idx - 1, inIndex);
    root->right = buildTree(preorder, preStart + leftSize + 1, preEnd,
                            inorder, idx + 1, inEnd, inIndex);

    return root;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> preorder(n), inorder(n);
    for (int i = 0; i < n; i++) cin >> preorder[i];
    for (int i = 0; i < n; i++) cin >> inorder[i];

    unordered_map<int,int> inIndex;
    for (int i = 0; i < n; i++) inIndex[inorder[i]] = i;

    TreeNode* root = buildTree(preorder, 0, n - 1, inorder, 0, n - 1, inIndex);

    queue<TreeNode*> q;
    q.push(root);
    while (!q.empty()) {
        int sz = q.size();
        for (int i = 0; i < sz; i++) {
            TreeNode* node = q.front(); q.pop();
            cout << node->val << " ";
            if (node->left) q.push(node->left);
            if (node->right) q.push(node->right);
        }
    }
    cout << "\n";

    return 0;
}