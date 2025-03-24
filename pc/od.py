
def sum_num(a,b):
    return a + b


def longestPalinfrome(s):
    n = len(s)
    if(n < 2):
        return s

    max_len = 1
    begin = 0
    #dp[i][j]表示s[i..j]是否是回文串
    dp = [[False] * n for _ in range(n)]
    for i in range(n):
        dp[i][i] = True

    #枚举子串长度
    for l in range(2, n+1):
        #枚举左边界
        for i in range(n):
            #由l和i可以确定右边界，即j-i+1=l
            j = l+i-1
            #如果右边界越界，就可以退出当前循环
            if j>=n:
                break
            print(i,j)
            if(s[i] != s[j]):
                dp[i][j] = False
            else:
                if(j-i<3):
                    dp[i][j] = True
                else:
                    dp[i][j] = dp[i+1][j-1]

            if dp[i][j] and j - i + 1 > max_len:
                max_len = j-i+1
                begin = i
    return s[begin:begin+max_len]


# 判断给定字符串是否是有效字符串
def is_valid_str(s):
    _map = {')':'(', '}':'{', ']':'['}
    _stack = []
    for char in s:
        if(char in _map):
            #如果栈为空，或者栈顶元素不是对应的左括号，就返回false
            if len(_stack) == 0 or _stack[-1] != _map[char]:
                return False
            _stack.pop() # 匹配成功，弹出
        else:
            #直接入栈
            _stack.append(char)
    #如果处理完毕后，栈为空，说明正确匹配
    if(len(_stack) == 0):
        return True
    else:
        return False

if __name__ == '__main__':
    # print(sum_num(1,2))
    # print(longestPalinfrome('ababac'))
    # print(is_valid_str("()"))
    # print(is_valid_str("()[]{}"))
    # print(is_valid_str("(]"))
    # print(is_valid_str("([])"))

    print(is_valid_str("][{()}"))
