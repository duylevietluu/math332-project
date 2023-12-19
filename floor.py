from gurobipy import Model, GRB
import re

# regex patterns for parsing constraints
patterns = {
    "width": r"box (\d+) has width of ([-+e\d.]+)",
    "height": r"box (\d+) has height of ([-+e\d.]+)",
    "position": r"box (\d+) is to the (left|bottom) of box (\d+)",
    "area": r"box (\d+) has area of at least ([-+e\d.]+)",
    "ratio": r"box (\d+) has aspect ratio of (at least|at most) ([-+e\d.]+)",
    "horizontal_align": r"(top|center|bottom) of box (\d+) aligns horizontally with (top|center|bottom) of box (\d+)",
    "vertical_align": r"(left|center|right) of box (\d+) aligns vertically with (left|center|right) of box (\d+)",
    "symmetry": r"box (\d+) and box (\d+) are symmetric through axis (x|y)=([-+e\d.]+)",
    "similarity": r"box (\d+) is ([-+e\d.]+)-scaled translate of box (\d+)",
    "containment": r"box (\d+) contains a point \(([-+e\d.]+),([-+e\d.]+)\)"
}

# human readable forms of constraints
forms = {
    "width": "box [int] has width of [float]",
    "height": "box [int] has height of [float]",
    "position": "box [int] is to the [left|bottom] of box [int]",
    "area": "box [int] has area of at least [float]",
    "ratio": "box [int] has aspect ratio of [at least|at most] [float]",
    "horizontal_align": "[top|center|bottom] of box [int] aligns horizontally with [top|center|bottom] of box [int]",
    "vertical_align": "[left|center|right] of box [int] aligns vertically with [left|center|right] of box [int]",
    "symmetry": "box [int] and box [int] are symmetric through axis [x|y]=[float]",
    "similarity": "box [int] is [float]-scaled translate of box [int]",
    "containment": "box [int] contains a point ([float],[float])"
}

def parse_match(constraint_type: str, constraint: str):
    """
    return the parsed match in tuple. 
    for example, in position constraint, it will return (0, "left", 2).
    throw exception if the constraint is invalid.
    """
    constraint_type = constraint_type.lower()
    constraint = constraint.lower()

    match = re.match(patterns[constraint_type], constraint)
    if not match:
        raise Exception("Invalid constraint")
    match = match.groups()

    if constraint_type == "width":
        box, width = int(match[0]), float(match[1])
        return (box, width)
    elif constraint_type == "height":
        box, height = int(match[0]), float(match[1])
        return (box, height)
    elif constraint_type == "position":
        box1, position, box2 = int(match[0]), match[1], int(match[2])
        return (box1, position, box2)
    elif constraint_type == "area":
        box, area = int(match[0]), float(match[1])
        return (box, area)
    elif constraint_type == "ratio":
        box, ratio_type, ratio = int(match[0]), match[1], float(match[2])
        return (box, ratio_type, ratio)
    elif constraint_type == "horizontal_align":
        align1, box1, align2, box2 = match[0], int(match[1]), match[2], int(match[3])
        return (align1, box1, align2, box2)
    elif constraint_type == "vertical_align":
        align1, box1, align2, box2 = match[0], int(match[1]), match[2], int(match[3])
        return (align1, box1, align2, box2)
    elif constraint_type == "symmetry":
        box1, box2, axis, axis_value = int(match[0]), int(match[1]), match[2], float(match[3])
        return (box1, box2, axis, axis_value)
    elif constraint_type == "similarity":
        box1, scale, box2 = int(match[0]), float(match[1]), int(match[2])
        return (box1, scale, box2)
    elif constraint_type == "containment":
        box, x1, y1 = int(match[0]), float(match[1]), float(match[2])
        return (box, x1, y1)
    else:
        raise Exception("Invalid constraint")


def solve(N, p, constraints, timeout=60):
    """parse the constraints and solve the problem using gurobi"""
    model = Model()
    model.setParam('TimeLimit', timeout)

    # add variables
    W = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
    H = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
    w = [model.addVar(lb=0, vtype=GRB.CONTINUOUS) for _ in range(N)]
    h = [model.addVar(lb=0, vtype=GRB.CONTINUOUS) for _ in range(N)]
    x = [model.addVar(lb=0, vtype=GRB.CONTINUOUS) for _ in range(N)]
    y = [model.addVar(lb=0, vtype=GRB.CONTINUOUS) for _ in range(N)]

    # set objective
    model.setObjective(2 * (W + H), GRB.MINIMIZE)

    # boundin box constraints
    for i in range(N):
        model.addConstr(x[i] + w[i] <= W)
        model.addConstr(y[i] + h[i] <= H)
    
    # relative positioning constraints
    # for every 2 boxes, they can be either left, right, top, or bottom of each other
    for i in range(N):
        for j in range(i+1, N):
            # add 4 binary variables
            l, r, b, t = (model.addVar(vtype=GRB.BINARY) for _ in range(4))

            # define l, r, t, b
            model.addConstr((l == 1) >> (x[i] + w[i] + p <= x[j]))
            model.addConstr((r == 1) >> (x[j] + w[j] + p <= x[i]))
            model.addConstr((b == 1) >> (y[i] + h[i] + p <= y[j]))
            model.addConstr((t == 1) >> (y[j] + h[j] + p <= y[i]))

            # XOR constraint
            model.addConstr(l + r <= 1)
            model.addConstr(b + t <= 1)

            # OR constraint
            model.addConstr(l + r + b + t >= 1)

    def parse_constraint(constraint_type: str, constraint: str):
        if constraint_type == "width":
            box, width = parse_match(constraint_type, constraint)
            model.addConstr(w[box] == width)
        elif constraint_type == "height":
            box, height = parse_match(constraint_type, constraint)
            model.addConstr(h[box] == height)
        elif constraint_type == "position":
            box1, position, box2 = parse_match(constraint_type, constraint)
            if position == "left":
                model.addConstr(x[box1] + w[box1] + p <= x[box2])
            else:
                model.addConstr(y[box1] + h[box1] + p <= y[box2])
        elif constraint_type == "area":
            box, area = parse_match(constraint_type, constraint)
            model.addConstr(w[box] * h[box] >= area)
        elif constraint_type == "ratio":
            box, ratio_type, ratio = parse_match(constraint_type, constraint)
            if ratio_type == "at least":
                model.addConstr(w[box] >= ratio * h[box])
            else:
                model.addConstr(w[box] <= ratio * h[box])
        elif constraint_type == "horizontal_align":
            align1, box1, align2, box2 = parse_match(constraint_type, constraint)
            match align1:
                case "top":
                    equation1 = y[box1] + h[box1]
                case "center":
                    equation1 = y[box1] + h[box1] / 2
                case "bottom":
                    equation1 = y[box1] 
            match align2:
                case "top":
                    equation2 = y[box2] + h[box2]
                case "center":
                    equation2 = y[box2] + h[box2] / 2
                case "bottom":
                    equation2 = y[box2]
            model.addConstr(equation1 == equation2)
        elif constraint_type == "vertical_align":
            align1, box1, align2, box2 = parse_match(constraint_type, constraint)
            match align1:
                case "left":
                    equation1 = x[box1]
                case "center":
                    equation1 = x[box1] + w[box1] / 2
                case "right":
                    equation1 = x[box1] + w[box1]
            match align2:
                case "left":
                    equation2 = x[box2]
                case "center":
                    equation2 = x[box2] + w[box2] / 2
                case "right":
                    equation2 = x[box2] + w[box2]
            model.addConstr(equation1 == equation2)
        elif constraint_type == "symmetry":
            box1, box2, axis, axis_value = parse_match(constraint_type, constraint)
            if axis == "x":
                model.addConstr(axis_value - (x[box1] + w[box1]/2) == (x[box2] + w[box2]/2) - axis_value)
            else:
                model.addConstr(axis_value - (y[box1] + h[box1]/2) == (y[box2] + h[box2]/2) - axis_value)
        elif constraint_type == "similarity":
            box1, scale, box2 = parse_match(constraint_type, constraint)
            model.addConstr(w[box1] == scale * w[box2])
            model.addConstr(h[box1] == scale * h[box2])
        elif constraint_type == "containment":
            box, x1, y1 = parse_match(constraint_type, constraint)
            model.addConstr(x[box] <= x1)
            model.addConstr(y[box] <= y1)
            model.addConstr(x[box] + w[box] >= x1)
            model.addConstr(y[box] + h[box] >= y1)
        else:
            raise Exception(f"Invalid constraint: {constraint}")
    
    # adding other constraints
    for constraint_type, constraint in constraints:
        parse_constraint(constraint_type, constraint)
            
    # optimize
    model.optimize()

    # if the model is infeasible
    if model.status == GRB.INFEASIBLE:
        raise Exception("Infeasible model")

    # if the model is inoptimal
    if model.status != GRB.OPTIMAL:
        print("Model is not optimal")
    
    return (
        model.objVal, 
        W.X, 
        H.X,
        [i.X for i in x],
        [i.X for i in y],
        [i.X for i in w],
        [i.X for i in h],
        model.status
    )


# a test for the solver
if __name__ == "__main__":
    N = 5
    p = 0.1
    constraints = [
        ("area", "box 0 has area of at least 1"),
        ("area", "box 1 has area of at least 1"),
        ("area", "box 2 has area of at least 1"),
        ("area", "box 3 has area of at least 1"),
        ("area", "box 4 has area of at least 1"),
        ("ratio", "box 0 has aspect ratio of at least 0.2"),
        ("ratio", "box 1 has aspect ratio of at least 0.2"),
        ("ratio", "box 2 has aspect ratio of at least 0.2"),
        ("ratio", "box 3 has aspect ratio of at least 0.2"),
        ("ratio", "box 4 has aspect ratio of at least 0.2"),
        ("ratio", "box 0 has aspect ratio of at most 5"),
        ("ratio", "box 1 has aspect ratio of at most 5"),
        ("ratio", "box 2 has aspect ratio of at most 5"),
        ("ratio", "box 3 has aspect ratio of at most 5"),
        ("ratio", "box 4 has aspect ratio of at most 5"),
    ]
    
    peri, W, H, x_arr, y_arr, w_arr, h_arr = solve(N, p, constraints)

    # Visualize the result
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.add_patch(plt.Rectangle((0, 0), W, H, edgecolor='black', facecolor='white'))
    for i, (x, y, w, h) in enumerate(zip(x_arr, y_arr, w_arr, h_arr)):
        ax.add_patch(plt.Rectangle((x, y), w, h, edgecolor='black', facecolor='lightgrey'))
        plt.text(x + w/2, y + h/2, f'{i}', ha='center', va='center')

    plt.xlim(0, W)
    plt.ylim(0, H)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()
