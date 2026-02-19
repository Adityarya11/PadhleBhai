class Solution {
private:
    int winner(int l,int r,vector<int>&nums){
        
        if(r-l<2){
            if(r-l==1)return max(nums[l],nums[l+1]);
            if(r==l)return nums[l];
        }
        int pickL = nums[l] + min(winner(l+2, r, nums), winner(l+1, r-1, nums));
        int pickR = nums[r] + min(winner(l, r-2, nums), winner(l+1, r-1, nums));
        return max(pickL, pickR);

        
    }
public:
    bool predictTheWinner(vector<int>& nums) {
        int n=nums.size();
        int player1= winner(0,n-1,nums);
        int sum=accumulate(nums.begin(),nums.end(),0);
        if(player1>=(sum+1)/2)return true;
        return false;
    }
};