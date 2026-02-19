#include <unordered_map>
#include <vector>

class Node
{
public:
    int val;
    std::vector<Node *> neighbors;
    Node() : val(0) {}
    Node(int _val) : val(_val) {}
    Node(int _val, std::vector<Node *> _neighbors) : val(_val), neighbors(_neighbors) {}
};

class Solution
{
public:
    unordered_map<Node *, Node *> mp;
    // old----->new

    Node *cloneGraph(Node *node)
    {
        if (!node)
            return nullptr;

        queue<Node *> q;
        q.push(node);
        mp[node] = new Node(node->val);

        while (!q.empty())
        {
            auto curr = q.front();
            q.pop();

            for (auto child : curr->neighbors)
            {
                if (mp.find(child) == mp.end())
                {
                    // child not cloned yet
                    mp[child] = new Node(child->val);
                    q.push(child);
                }
                mp[curr]->neighbors.push_back(mp[child]);
            }
        }
        return mp[node];
    }
};