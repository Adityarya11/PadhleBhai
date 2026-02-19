class Solution
{
public:
    int howManyBorders(vector<vector<int>> &grid, int row, int column)
    {
        int borders = 0;
        const vector<int> dx = {-1, 1, 0, 0};
        const vector<int> dy = {0, 0, -1, 1};
        int n = grid.size();
        int m = grid[0].size();

        for (int k = 0; k < 4; k++)
        {
            int nr = row + dx[k];
            int nc = column + dy[k];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m || grid[nr][nc] == 0)
            {
                borders++;
            }
        }
        return borders;
    }
    int islandPerimeter(vector<vector<int>> &grid)
    {
        int perimeter = 0;
        for (int i = 0; i < grid.size(); i++)
        {
            for (int j = 0; j < grid[i].size(); j++)
            {
                if (grid[i][j] == 1)
                {
                    perimeter += howManyBorders(grid, i, j);
                }
            }
        }
        return perimeter;
    }
};