def dim_color(color, factor=0.4):
    """Затемняет цвет, сохраняя его оттенок. Factor 1.0 = оригинал, 0.0 = черный."""
    r, g, b = color[:3]
    return (
        max(0, int(r * factor)),
        max(0, int(g * factor)),
        max(0, int(b * factor))
    )


def resolve_cells(cells_spec, grid_cols, grid_rows):
    if isinstance(cells_spec, list):
        return [tuple(c) for c in cells_spec]
    if cells_spec == "corners":
        return [(0, 0), (grid_cols - 1, 0), (0, grid_rows - 1), (grid_cols - 1, grid_rows - 1)]
    elif cells_spec == "edges":
        edges = set()
        for x in range(grid_cols):
            edges.add((x, 0))
            edges.add((x, grid_rows - 1))
        for y in range(grid_rows):
            edges.add((0, y))
            edges.add((grid_cols - 1, y))
        return list(edges)
    elif cells_spec == "center":
        return [(grid_cols // 2, grid_rows // 2)]
    return []


def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def eval_step_expr(expr, step):
    expr = expr.strip()
    if "|" in expr:
        return any(eval_step_expr(p.strip(), step) for p in expr.split("|"))
    if "&" in expr:
        return all(eval_step_expr(p.strip(), step) for p in expr.split("&"))
    if expr.startswith("!"):
        return not eval_step_expr(expr[1:], step)

    if expr == "even":
        return step % 2 == 0
    elif expr == "odd":
        return step % 2 == 1
    elif expr == "prime":
        return is_prime(step)
    elif expr.startswith("div:"):
        return step % int(expr.split(":")[1]) == 0
    elif expr.startswith("mod:"):
        parts = expr.split(":")
        return step % int(parts[1]) == int(parts[2])
    elif expr.startswith("range:"):
        parts = expr.split(":")
        return int(parts[1]) <= step <= int(parts[2])
    elif expr.startswith("gt:"):
        return step > int(expr.split(":")[1])
    elif expr.startswith("lt:"):
        return step < int(expr.split(":")[1])
    elif expr.startswith("gte:"):
        return step >= int(expr.split(":")[1])
    elif expr.startswith("lte:"):
        return step <= int(expr.split(":")[1])
    return False
