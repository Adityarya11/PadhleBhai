# primal

import pulp

# Define model
primal = pulp.LpProblem('Solar_Distribution', pulp.LpMinimize)

# Decision variables
x11 = pulp.LpVariable('P1_A', lowBound=0)
x12 = pulp.LpVariable('P1_B', lowBound=0)
x13 = pulp.LpVariable('P1_C', lowBound=0)
x14 = pulp.LpVariable('P1_D', lowBound=0)

x21 = pulp.LpVariable('P2_A', lowBound=0)
x22 = pulp.LpVariable('P2_B', lowBound=0)
x23 = pulp.LpVariable('P2_C', lowBound=0)
x24 = pulp.LpVariable('P2_D', lowBound=0)

# Objective function (minimize transmission cost)
primal += 2*x11 + 3*x12 + 4*x13 + 5*x14 + 3*x21 + 1*x22 + 2*x23 + 4*x24

# Supply constraints
primal += x11 + x12 + x13 + x14 <= 200, "P1_Supply"
primal += x21 + x22 + x23 + x24 <= 180, "P2_Supply"

# Demand constraints
primal += x11 + x21 == 120, "Demand_A"
primal += x12 + x22 == 100, "Demand_B"
primal += x13 + x23 == 80,  "Demand_C"
primal += x14 + x24 == 60,  "Demand_D"

# Solve
primal.solve()
print("Minimum Transmission Cost:", pulp.value(primal.objective))
for v in primal.variables():
    print(v.name, "=", v.varValue)

# Shadow prices
for name, c in primal.constraints.items():
    print(name, "Shadow Price =", c.pi, " Slack =", c.slack)


# Dual

import pulp

# Define model
dual = pulp.LpProblem("Solar_Distribution_Dual", pulp.LpMaximize)

# Dual variables
u1 = pulp.LpVariable("P1_Supply", lowBound=0)   # supply P1
u2 = pulp.LpVariable("P2_Supply", lowBound=0)   # supply P2
vA = pulp.LpVariable("Demand_A")
vB = pulp.LpVariable("Demand_B")
vC = pulp.LpVariable("Demand_C")
vD = pulp.LpVariable("Demand_D")

# Objective function
dual += 200*u1 + 180*u2 + 120*vA + 100*vB + 80*vC + 60*vD

# Constraints (one for each primal variable)
dual += u1 + vA <= 2   # P1→A
dual += u1 + vB <= 3   # P1→B
dual += u1 + vC <= 4   # P1→C
dual += u1 + vD <= 5   # P1→D

dual += u2 + vA <= 3   # P2→A
dual += u2 + vB <= 1   # P2→B
dual += u2 + vC <= 2   # P2→C
dual += u2 + vD <= 4   # P2→D

# Solve
dual.solve()
print("Optimal Value (W):", pulp.value(dual.objective))
for v in dual.variables():
    print(v.name, "=", v.varValue)
