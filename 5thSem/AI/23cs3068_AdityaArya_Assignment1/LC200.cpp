#include <vector>
#include <functional>
using namespace std;

class Solution
{
public:
    int numIslands(vector<vector<char>> &grid)
    {
        int rowCount = grid.size();
        int colCount = grid[0].size();
        int islandCount = 0;

        int directions[5] = {-1, 0, 1, 0, -1};

        function<void(int, int)> dfs = [&](int row, int col)
        {
            grid[row][col] = '0';

            for (int k = 0; k < 4; ++k)
            {
                int newRow = row + directions[k];
                int newCol = col + directions[k + 1];

                if (newRow >= 0 && newRow < rowCount && newCol >= 0 && newCol < colCount && grid[newRow][newCol] == '1')
                {
                    dfs(newRow, newCol);
                }
            }
        };

        for (int row = 0; row < rowCount; ++row)
        {
            for (int col = 0; col < colCount; ++col)
            {

                if (grid[row][col] == '1')
                {
                    dfs(row, col);
                    islandCount++;
                }
            }
        }
        return islandCount;
    }
};
