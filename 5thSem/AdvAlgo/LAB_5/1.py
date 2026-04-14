# Primal

import pulp

# Define model
primal = pulp.LpProblem("Diet_MinCost", pulp.LpMinimize)

# Decision variables
x1 = pulp.LpVariable('Chicken', lowBound=0)
x2 = pulp.LpVariable('Milk', lowBound=0)
x3 = pulp.LpVariable('Rice', lowBound=0)
x4 = pulp.LpVariable('Fruits', lowBound=0)

# Objective
primal += 50*x1 + 30*x2 + 20*x3 + 25*x4

# Constraints
primal += 25*x1 + 10*x2 + 4*x3 + 2*x4 >= 100, "Protein"
primal += 5*x1 + 12*x2 + 40*x3 + 20*x4 >= 200, "Carbs"
primal += 2*x1 + 4*x2 + 1*x3 + 6*x4 >= 20, "Vitamins"

# Solve
primal.solve()
print("Optimal Cost:", pulp.value(primal.objective))
for v in primal.variables():
    print(v.name, "=", v.varValue)


# DUAL

import pulp

# Define model (dual is maximization)
dual = pulp.LpProblem("Diet_Dual", pulp.LpMaximize)

# Dual variables
y1 = pulp.LpVariable('Protein', lowBound=0)   # corresponds to protein constraint
y2 = pulp.LpVariable('Carbs', lowBound=0)     # corresponds to carbs constraint
y3 = pulp.LpVariable('Vitamins', lowBound=0)  # corresponds to vitamins constraint

# Objective (maximize total value of nutrient requirements)
dual += 100*y1 + 200*y2 + 20*y3

# Constraints (one for each food item, ≤ cost of that food)
dual += 25*y1 + 5*y2 + 2*y3 <= 50, "Chicken"
dual += 10*y1 + 12*y2 + 4*y3 <= 30, "Milk"
dual += 4*y1 + 40*y2 + 1*y3 <= 20, "Rice"
dual += 2*y1 + 20*y2 + 6*y3 <= 25, "Fruits"

# Solve
dual.solve()
print("Optimal Value (W):", pulp.value(dual.objective))
for v in dual.variables():
    print(v.name, "=", v.varValue)

# Shadow prices and slack (not usually needed for dual, but you can print)
for name, c in dual.constraints.items():
    print(name, "Slack =", c.slack)
