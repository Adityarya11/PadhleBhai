#include <iostream>
#include <vector>
#include <stack>
#include <limits.h>
using namespace std;

const int V = 10;

bool dfs(int residualGraph[V][V], int source, int sink, vector<int> &parent)
{
    vector<bool> visited(V, false);
    stack<int> s;
    s.push(source);
    visited[source] = true;

    while (!s.empty())
    {
        int u = s.top();
        s.pop();

        for (int v = 0; v < V; v++)
        {
            if (!visited[v] && residualGraph[u][v] > 0)
            {
                s.push(v);
                parent[v] = u;
                visited[v] = true;

                if (v == sink)
                    return true;
            }
        }
    }
    return false;
}

int fordFulkerson(int graph[V][V], int source, int sink)
{
    int u, v;
    int residualGraph[V][V];

    for (u = 0; u < V; u++)
        for (v = 0; v < V; v++)
            residualGraph[u][v] = graph[u][v];

    vector<int> parent(V);
    int maxFlow = 0;

    while (dfs(residualGraph, source, sink, parent))
    {
        int pathFlow = INT_MAX;

        for (v = sink; v != source; v = parent[v])
        {
            u = parent[v];
            pathFlow = min(pathFlow, residualGraph[u][v]);
        }

        for (v = sink; v != source; v = parent[v])
        {
            u = parent[v];
            residualGraph[u][v] -= pathFlow;
            residualGraph[v][u] += pathFlow;
        }

        maxFlow += pathFlow;
    }

    return maxFlow;
}

int main()
{
    int graph[V][V] = {0};

    graph[0][2] = 20;
    graph[0][3] = 15;
    graph[1][3] = 10;
    graph[1][4] = 5;
    graph[2][5] = 10;
    graph[3][5] = 5;
    graph[3][6] = 10;
    graph[4][6] = 10;
    graph[4][7] = 5;

    graph[8][0] = 1000;
    graph[8][1] = 1000;

    graph[5][9] = 1000;
    graph[6][9] = 1000;
    graph[7][9] = 1000;

    int source = 8;
    int sink = 9;

    int maxFlowBefore = fordFulkerson(graph, source, sink);
    cout << "1. Max water supply/hour BEFORE removing edge 1 to 4: " << maxFlowBefore << " kL/h" << endl;

    graph[1][4] = 0;

    int maxFlowAfter = fordFulkerson(graph, source, sink);
    cout << "2. Max water supply/hour AFTER removing edge 1 to 4: " << maxFlowAfter << " kL/h" << endl;

    int inputs[V] = {0};
    for (int u = 0; u < V; u++)
    {
        for (int v = 0; v < V; v++)
        {
            if (graph[u][v] > 0)
            {
                inputs[v]++;
            }
        }
    }

    cout << "3. Overloaded Reservoirs (multiple incoming pipes):" << endl;
    for (int i = 2; i <= 4; i++)
    {
        if (inputs[i] > 1)
        {
            cout << "Reservoir R" << (i - 1) << " is overloaded (inputs: " << inputs[i] << ")" << endl;
        }
    }

    cout << "Suggestion: Add balancing routes or limit upstream flow to reduce overload.\n";

    return 0;
}
