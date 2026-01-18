from src.logic.operators import get_operator
from src.logic.sequence import check_sequence_condition
from src.logic.steps import parse_steps
from src.utils.misc import eval_step_expr, resolve_cells


def check_condition(cond, path, player_pos, cols, rows, player_history=None):
    """Проверяет одно условие. player_history нужен для check=sequence."""
    check = cond.get("check", "")
    cells = resolve_cells(cond.get("cells", []), cols, rows)
    match = cond.get("match", "all")

    if check == "group":
        logic = cond.get("logic", "AND").upper()
        items = cond.get("items", [])
        results = [check_condition(item, path, player_pos, cols, rows, player_history)
                   for item in items]
        if logic == "AND":
            return all(results)
        elif logic == "OR":
            return any(results)
        elif logic == "NOT":
            return not results[0] if results else True
        elif logic == "XOR":
            return sum(results) == 1
        return False

    if check == "sequence":
        if player_history is None:
            return False
        return check_sequence_condition(cond, player_history)

    if check == "visit":
        visit_counts = {}
        for pos in path:
            visit_counts[pos] = visit_counts.get(pos, 0) + 1

        if "min" in cond or "max" in cond:
            min_c, max_c = cond.get("min", 0), cond.get("max", 999999)
            if match == "any":
                return any(min_c <= visit_counts.get(c, 0) <= max_c for c in cells)
            return all(min_c <= visit_counts.get(c, 0) <= max_c for c in cells)

        count = cond.get("count", 1)

        if count == 0:
            default_op = "=="
        else:
            default_op = ">="
        op_func = get_operator(cond.get("operator", default_op), default_op)

        if match == "any":
            return any(op_func(visit_counts.get(c, 0), count) for c in cells)
        return all(op_func(visit_counts.get(c, 0), count) for c in cells)

    if check == "at_steps":
        mode = cond.get("mode", "require")
        cells_set = set(cells)

        if "step_expr" in cond:
            expr = cond["step_expr"]
            if mode == "avoid":
                for i, pos in enumerate(path):
                    if pos in cells_set and eval_step_expr(expr, i):
                        return False
                return True
            else:
                cell_valid = {c: False for c in cells}
                for i, pos in enumerate(path):
                    if pos in cells_set and eval_step_expr(expr, i):
                        cell_valid[pos] = True
                return any(cell_valid.values()) if match == "any" else all(
                    cell_valid.get(c, False) for c in cells
                )

        target_steps = parse_steps(cond)
        cell_steps = {}
        for i, pos in enumerate(path):
            if pos not in cell_steps:
                cell_steps[pos] = set()
            cell_steps[pos].add(i)

        if mode == "avoid":
            for i, pos in enumerate(path):
                if pos in cells_set and i in target_steps:
                    return False
            return True
        else:
            if match == "any":
                return any(
                    c in cell_steps and target_steps.issubset(cell_steps[c]) for c in cells
                )
            return all(
                c in cell_steps and target_steps.issubset(cell_steps[c]) for c in cells
            )

    if check == "end_at":
        return tuple(player_pos) in cells

    if check == "order":
        first_visits = {}
        for i, pos in enumerate(path):
            if pos not in first_visits:
                first_visits[pos] = i
        prev = -1
        for c in cells:
            if c not in first_visits or first_visits[c] <= prev:
                return False
            prev = first_visits[c]
        return True

    if check == "consecutive":
        count = cond.get("count", 2)

        def max_consecutive(cell):
            max_c = current = 0
            for pos in path:
                if pos == cell:
                    current += 1
                    max_c = max(max_c, current)
                else:
                    current = 0
            return max_c

        if match == "any":
            return any(max_consecutive(c) >= count for c in cells)
        return all(max_consecutive(c) >= count for c in cells)

    if check == "no_revisit":
        exceptions = resolve_cells(cond.get("except", []), cols, rows)
        visited = set()
        for pos in path:
            if pos in exceptions:
                continue
            if pos in visited:
                return False
            visited.add(pos)
        return True

    if check == "total_steps":
        count = cond.get("count", 0)
        default_op = "==" if count == 0 else "=="
        op_func = get_operator(cond.get("operator", default_op), default_op)
        return op_func(len(path) - 1, count)

    return False


def check_all_conditions(conditions, path, player_pos, cols, rows, player_history=None):
    return all(check_condition(c, path, player_pos, cols, rows, player_history)
               for c in conditions)
