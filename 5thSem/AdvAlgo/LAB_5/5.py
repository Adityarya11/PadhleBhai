## Primal

import pulp

# Define model
primal = pulp.LpProblem("Emergency_Fuel_Allocation", pulp.LpMaximize)

# Decision variables
xX = pulp.LpVariable('Fuel_X', lowBound=0)  # Fuel sent to City X
xY = pulp.LpVariable('Fuel_Y', lowBound=0)  # Fuel sent to City Y
xZ = pulp.LpVariable('Fuel_Z', lowBound=0)  # Fuel sent to City Z

# Objective function (maximize profit)
primal += 40*xX + 50*xY + 60*xZ

# Constraints
primal += xX + xY + xZ <= 500, "Depot_Supply"

primal += xX <= 200, "Demand_X"
primal += xY <= 220, "Demand_Y"
primal += xZ <= 180, "Demand_Z"

primal += xX <= 180, "Pipeline_X"
primal += xY <= 200, "Pipeline_Y"
primal += xZ <= 150, "Pipeline_Z"

# Solve
primal.solve()
print("Maximum Profit:", pulp.value(primal.objective))
for v in primal.variables():
    print(v.name, "=", v.varValue)

# Shadow prices
for name, c in primal.constraints.items():
    print(name, "Shadow Price =", c.pi, " Slack =", c.slack)


## Dual

import pulp

# Define model
dual = pulp.LpProblem("Emergency_Fuel_Allocation_Dual", pulp.LpMinimize)

# Dual variables
u = pulp.LpVariable("Depot_Supply", lowBound=0)

dX = pulp.LpVariable("Demand_X", lowBound=0)
dY = pulp.LpVariable("Demand_Y", lowBound=0)
dZ = pulp.LpVariable("Demand_Z", lowBound=0)

pX = pulp.LpVariable("Pipeline_X", lowBound=0)
pY = pulp.LpVariable("Pipeline_Y", lowBound=0)
pZ = pulp.LpVariable("Pipeline_Z", lowBound=0)

# Objective function
dual += 500*u + 200*dX + 220*dY + 180*dZ + 180*pX + 200*pY + 150*pZ

# Constraints (profit coefficients from primal)
dual += u + dX + pX >= 40, "City_X"
dual += u + dY + pY >= 50, "City_Y"
dual += u + dZ + pZ >= 60, "City_Z"

# Solve
dual.solve()
print("Optimal Value (W):", pulp.value(dual.objective))
for v in dual.variables():
    print(v.name, "=", v.varValue)
