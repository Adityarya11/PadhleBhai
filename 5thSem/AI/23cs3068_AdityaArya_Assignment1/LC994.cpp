#include <vector>
#include <queue>
using namespace std;

class Solution
{
public:
    int orangesRotting(vector<vector<int>> &grid)
    {
        int m = grid.size(), n = grid[0].size();
        queue<pair<int, int>> q;
        int fresh = 0;

        for (int i = 0; i < m; i++)
        {
            for (int j = 0; j < n; j++)
            {
                if (grid[i][j] == 2)
                {
                    q.push({i, j});
                }
                else if (grid[i][j] == 1)
                {
                    fresh++;
                }
            }
        }

        if (fresh == 0)
            return 0;

        int minutes = -1;
        vector<int> dir = {0, 1, 0, -1, 0};

        while (!q.empty())
        {
            int sz = q.size();
            minutes++;
            while (sz--)
            {
                auto [r, c] = q.front();
                q.pop();
                for (int k = 0; k < 4; k++)
                {
                    int nr = r + dir[k], nc = c + dir[k + 1];

                    if (nr >= 0 && nc >= 0 && nr < m && nc < n && grid[nr][nc] == 1)
                    {
                        grid[nr][nc] = 2;
                        fresh--;
                        q.push({nr, nc});
                    }
                }
            }
        }
        return (fresh == 0) ? minutes : -1;
    }
};