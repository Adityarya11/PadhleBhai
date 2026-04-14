# Primal
import pulp

# Define model
primal = pulp.LpProblem("Refinery_Workforce", pulp.LpMinimize)

# Decision variables
x1 = pulp.LpVariable('Perm_Morning', lowBound=0)
x2 = pulp.LpVariable('Perm_Afternoon', lowBound=0)
x3 = pulp.LpVariable('Perm_Night', lowBound=0)
y1 = pulp.LpVariable('Contract_Morning', lowBound=0)
y2 = pulp.LpVariable('Contract_Afternoon', lowBound=0)
y3 = pulp.LpVariable('Contract_Night', lowBound=0)

# Objective
primal += 500*x1 + 450*x2 + 600*x3 + 700*(y1+y2+y3)

# Constraints
primal += x1 + y1 >= 6, "Morning"
primal += x2 + y2 >= 5, "Afternoon"
primal += x3 + y3 >= 4, "Night"
primal += x1 + x2 + x3 <= 12, "Perm_Availability"

# Solve
primal.solve()
print("Minimum Wage Expenditure:", pulp.value(primal.objective))
for v in primal.variables():
    print(v.name, "=", v.varValue)

# Shadow prices
for name, c in primal.constraints.items():
    print(name, "Shadow Price =", c.pi, " Slack =", c.slack)


# Dual

import pulp

# Define model (dual is maximization)
dual = pulp.LpProblem("Refinery_Workforce_Dual", pulp.LpMaximize)

# Dual variables
u1 = pulp.LpVariable('Morning', lowBound=0)
u2 = pulp.LpVariable('Afternoon', lowBound=0)
u3 = pulp.LpVariable('Night', lowBound=0)
v  = pulp.LpVariable('Permanent', lowBound=0)

# Objective
dual += 6*u1 + 5*u2 + 4*u3 - 12*v

# Constraints
dual += u1 - v <= 500, "Perm_Morning"
dual += u2 - v <= 450, "Perm_Afternoon"
dual += u3 - v <= 600, "Perm_Night"
dual += u1 <= 700, "Contract_Morning"
dual += u2 <= 700, "Contract_Afternoon"
dual += u3 <= 700, "Contract_Night"

# Solve
dual.solve()
print("Optimal Value (W):", pulp.value(dual.objective))
for var in dual.variables():
    print(var.name, "=", var.varValue)
