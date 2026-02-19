#include <bits/stdc++.h>
using namespace std;

map<char, vector<string>> g;
map<char, set<char>> f;
set<char> v;

void fr(char c)
{
    for (auto s : g[c])
    {
        if (!isupper(s[0]))
        {
            f[c].insert(s[0]);
        }
        else
        {
            for (char x : s)
            {
                if (isupper(x))
                {
                    fr(x);
                    for (char y : f[x])
                        if (y != '#')
                            f[c].insert(y);
                    if (f[x].count('#') == 0)
                        break;
                }
                else
                {
                    f[c].insert(x);
                    break;
                }
            }
        }
    }
}

int main()
{
    int n;
    cin >> n;
    while (n--)
    {
        string s;
        cin >> s;
        char l = s[0];
        string r = s.substr(2);
        g[l].push_back(r);
        v.insert(l);
    }
    for (char c : v)
        fr(c);
    for (char c : v)
    {
        cout << "FIRST(" << c << ") = { ";
        for (char x : f[c])
            cout << x << " ";
        cout << "}" << endl;
    }
}

// Q2. Write a C++ program to compute the FOLLOW set for all non-terminals of a given grammar

#include <bits/stdc++.h>
using namespace std;

map<char, vector<string>> g;
map<char, set<char>> f, fo;
set<char> v;
char s0;

void fr(char c)
{
    for (auto s : g[c])
    {
        if (!isupper(s[0]))
        {
            f[c].insert(s[0]);
        }
        else
        {
            for (char x : s)
            {
                if (isupper(x))
                {
                    fr(x);
                    for (char y : f[x])
                        if (y != '#')
                            f[c].insert(y);
                    if (!f[x].count('#'))
                        break;
                }
                else
                {
                    f[c].insert(x);
                    break;
                }
            }
        }
    }
}

int main()
{
    int n;
    cin >> n;
    while (n--)
    {
        string s;
        cin >> s;
        char l = s[0];
        if (g.empty())
            s0 = l;
        string r = s.substr(2);
        g[l].push_back(r);
        v.insert(l);
    }
    for (char c : v)
        fr(c);
    fo[s0].insert('$');
    bool ch = true;
    while (ch)
    {
        ch = false;
        for (auto p : g)
        {
            char l = p.first;
            for (auto r : p.second)
            {
                for (int i = 0; i < r.size(); i++)
                {
                    if (isupper(r[i]))
                    {
                        if (i + 1 < r.size())
                        {
                            if (isupper(r[i + 1]))
                            {
                                for (char x : f[r[i + 1]])
                                    if (x != '#' && !fo[r[i]].count(x))
                                    {
                                        fo[r[i]].insert(x);
                                        ch = true;
                                    }
                            }
                            else
                            {
                                if (!fo[r[i]].count(r[i + 1]))
                                {
                                    fo[r[i]].insert(r[i + 1]);
                                    ch = true;
                                }
                            }
                        }
                        else
                        {
                            for (char x : fo[l])
                                if (!fo[r[i]].count(x))
                                {
                                    fo[r[i]].insert(x);
                                    ch = true;
                                }
                        }
                    }
                }
            }
        }
    }
    for (char c : v)
    {
        cout << "FOLLOW(" << c << ") = { ";
        for (char x : fo[c])
            cout << x << " ";
        cout << "}" << endl;
    }
}

// Q3. Write a C++ program to eliminate immediate left recursion from a grammar

#include <bits/stdc++.h>
using namespace std;

int main()
{
    string s;
    cin >> s;
    char l = s[0];
    string r = s.substr(2);
    int p = r.find('/');
    string a = r.substr(0, p);
    string b = r.substr(p + 1);
    cout << l << " = " << b << l << "'" << endl;
    cout << l << "' = " << a.substr(1) << l << "' | ε" << endl;
}

// Q.4 Write a C++ program to perform left factoring on a grammar.

#include <bits/stdc++.h>
using namespace std;

int main()
{
    string s1, s2, s3;
    cin >> s1 >> s2 >> s3;
    char l = s1[0];
    string r1 = s1.substr(2);
    string r2 = s2.substr(2);
    string r3 = s3.substr(2);
    string p = "";
    int i = 0;
    while (i < r1.size() && i < r2.size() && r1[i] == r2[i])
    {
        p += r1[i];
        i++;
    }
    cout << l << " = " << p << l << "'" << endl;
    cout << l << "' = "
         << r1.substr(p.size()) << " | "
         << r2.substr(p.size()) << " | "
         << r3.substr(1) << endl;
}
