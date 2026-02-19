#include <iostream>
#include <vector>
#include <limits.h> // For INT_MAX
#include <map>
#include <stack>
using namespace std;

const int V = 6; // Number of nodes

// Function to perform DFS and find path with available capacity
bool dfs(int residualGraph[V][V], int s, int t, vector<int> &parent)
{
    vector<bool> visited(V, false); // Track visited nodes
    stack<int> stack;
    stack.push(s);
    visited[s] = true;

    while (!stack.empty())
    {
        int u = stack.top();
        stack.pop();

        for (int v = 0; v < V; v++)
        {
            // If there's capacity and v is not visited
            if (!visited[v] && residualGraph[u][v] > 0)
            {
                stack.push(v);
                parent[v] = u;
                visited[v] = true;

                if (v == t)
                    return true; // Reached sink
            }
        }
    }

    return false; // No path found
}

// Ford-Fulkerson algorithm using DFS
int fordFulkerson(int graph[V][V], int source, int sink)
{
    int u, v;
    int residualGraph[V][V]; // Residual graph

    // Initialize residual graph with original capacities
    for (u = 0; u < V; u++)
        for (v = 0; v < V; v++)
            residualGraph[u][v] = graph[u][v];

    vector<int> parent(V); // Stores path
    int maxFlow = 0;

    // Augment the flow while there is path from source to sink
    while (dfs(residualGraph, source, sink, parent))
    {
        int pathFlow = INT_MAX;

        // Find minimum capacity in the path
        for (v = sink; v != source; v = parent[v])
        {
            u = parent[v];
            pathFlow = min(pathFlow, residualGraph[u][v]);
        }

        // Update residual capacities
        for (v = sink; v != source; v = parent[v])
        {
            u = parent[v];
            residualGraph[u][v] -= pathFlow;
            residualGraph[v][u] += pathFlow; // Reverse edge
        }

        maxFlow += pathFlow;
    }

    return maxFlow;
}

int main()
{
    // Graph from the question
    int graph[V][V] = {0};

    // Add edges and their capacities
    graph[0][1] = 16;
    graph[0][2] = 13;
    graph[1][2] = 10;
    graph[2][1] = 4;
    graph[1][3] = 12;
    graph[3][2] = 9;
    graph[2][4] = 14;
    graph[4][3] = 7;
    graph[3][5] = 20;
    graph[4][5] = 4;

    int source = 0, sink = 5;

    cout << "The maximum possible flow is: "
         << fordFulkerson(graph, source, sink) << endl;

    return 0;
}
