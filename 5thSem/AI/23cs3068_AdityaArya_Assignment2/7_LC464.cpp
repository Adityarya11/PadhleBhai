class Solution {
public:
unordered_map<int , bool>dp;
    bool solve(int mask, int a, int b, int currSum) {
        if(dp.count(mask))return dp[mask];
        for (int i = 1; i <= a; i++) {
             int bit = 1<<(i-1);
            if ((mask & bit) == 0){
                
                if (currSum + i >= b || !solve(mask|bit, a, b, currSum + i)) {

                    return dp[mask]=true;
                }

            }
        }
        return dp[mask]=false;
    }

    bool canIWin(int a, int b) {
        if ((a * (a + 1)) / 2 < b) return false; 
        
        return solve(0, a, b, 0);
    }
};