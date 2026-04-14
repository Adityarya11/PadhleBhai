# Primal
import pulp

# Define model
primal = pulp.LpProblem("Airline_Crew_Scheduling", pulp.LpMinimize)

# Decision variables
xA1 = pulp.LpVariable('TypeA_F1', lowBound=0)  # Type A crew for Flight 1
xA2 = pulp.LpVariable('TypeA_F2', lowBound=0)  # Type A crew for Flight 2
xA3 = pulp.LpVariable('TypeA_F3', lowBound=0)  # Type A crew for Flight 3

xB2 = pulp.LpVariable('TypeB_F2', lowBound=0)  # Type B crew for Flight 2
xB3 = pulp.LpVariable('TypeB_F3', lowBound=0)  # Type B crew for Flight 3

# Objective (minimize total cost)
primal += 12000*(xA1 + xA2 + xA3) + 9000*(xB2 + xB3)

# Flight requirements
primal += xA1 >= 5, "Flight1_Requirement"
primal += xA2 + xB2 >= 6, "Flight2_Requirement"
primal += xA3 + xB3 >= 4, "Flight3_Requirement"

# Availability constraints
primal += xA1 + xA2 + xA3 <= 10, "TypeA_Availability"
primal += xB2 + xB3 <= 8, "TypeB_Availability"

# Solve
primal.solve()
print("Minimum Crew Cost:", pulp.value(primal.objective))
for v in primal.variables():
    print(v.name, "=", v.varValue)

# Shadow prices
for name, c in primal.constraints.items():
    print(name, "Shadow Price =", c.pi, " Slack =", c.slack)


#dual

import pulp

# Define model
dual = pulp.LpProblem("Airline_Crew_Scheduling_Dual", pulp.LpMaximize)

# Dual variables
y1 = pulp.LpVariable("Flight1", lowBound=0)    # Requirement for Flight 1
y2 = pulp.LpVariable("Flight2", lowBound=0)    # Requirement for Flight 2
y3 = pulp.LpVariable("Flight3", lowBound=0)    # Requirement for Flight 3
zA = pulp.LpVariable("TypeA", lowBound=0)      # Availability of Type A crew
zB = pulp.LpVariable("TypeB", lowBound=0)      # Availability of Type B crew

# Objective
dual += 5*y1 + 6*y2 + 4*y3 - 10*zA - 8*zB

# Constraints (cost restrictions for each primal variable)
dual += y1 - zA <= 12000, "TypeA_F1"
dual += y2 - zA <= 12000, "TypeA_F2"
dual += y3 - zA <= 12000, "TypeA_F3"

dual += y2 - zB <= 9000, "TypeB_F2"
dual += y3 - zB <= 9000, "TypeB_F3"

# Solve
dual.solve()
print("Optimal Value (W):", pulp.value(dual.objective))
for v in dual.variables():
    print(v.name, "=", v.varValue)
