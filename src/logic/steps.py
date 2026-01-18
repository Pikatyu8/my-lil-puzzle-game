from src.utils.misc import eval_step_expr


def parse_steps(condition, max_steps=500):
    result = set()
    if "step_expr" in condition:
        for s in range(max_steps):
            if eval_step_expr(condition["step_expr"], s):
                result.add(s)
        return result
    if "step" in condition:
        result.add(condition["step"])
    if "steps" in condition:
        result.update(condition["steps"])
    if "step_range" in condition:
        start, end = condition["step_range"]
        result.update(range(start, end + 1))
    return result


def format_steps(condition):
    if "step_expr" in condition:
        expr = condition["step_expr"]
        for old, new in [("even", "2n"), ("odd", "2n+1"), ("prime", "P")]:
            expr = expr.replace(old, new)
        return expr.replace("div:", "÷").replace("range:", "")

    parts = []
    if "step" in condition:
        parts.append(str(condition["step"]))
    if "steps" in condition:
        steps = condition["steps"]
        parts.append(",".join(map(str, steps)) if len(steps) <= 3 else f"{min(steps)}..{max(steps)}")
    if "step_range" in condition:
        s, e = condition["step_range"]
        parts.append(f"{s}-{e}")
    return ",".join(parts) if parts else "?"
