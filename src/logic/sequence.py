from src.logic.operators import OP_SYMBOLS, get_operator


def normalize_moves(moves_spec):
    """Нормализует спецификацию ходов в список."""
    if isinstance(moves_spec, str):
        mapping = {"up": "u", "down": "d", "left": "l", "right": "r"}
        result = []
        for m in moves_spec.lower().split():
            if m in mapping:
                result.append(mapping[m])
            elif m in ["u", "d", "l", "r"]:
                result.append(m)
        return result
    elif isinstance(moves_spec, list):
        mapping = {"up": "u", "down": "d", "left": "l", "right": "r"}
        return [mapping.get(m.lower(), m.lower()) for m in moves_spec
                if m.lower() in ["u", "d", "l", "r", "up", "down", "left", "right"]]
    return []


def count_sequence_occurrences(history, seq, overlapping=False):
    """
    Подсчитывает количество вхождений последовательности.
    """
    if not seq or len(seq) > len(history):
        return 0

    count = 0
    i = 0
    while i <= len(history) - len(seq):
        if history[i:i+len(seq)] == seq:
            count += 1
            i += 1 if overlapping else len(seq)
        else:
            i += 1
    return count


def check_sequence_match(history, seq, mode, min_count=1):
    """
    Проверяет соответствие последовательности.
    """
    if not seq:
        return True

    if mode == "exact":
        return history == seq
    elif mode == "starts_with":
        return len(history) >= len(seq) and history[:len(seq)] == seq
    elif mode == "ends_with":
        return len(history) >= len(seq) and history[-len(seq):] == seq
    elif mode == "not_contains":
        return count_sequence_occurrences(history, seq) == 0
    else:  # contains (default)
        return count_sequence_occurrences(history, seq) >= min_count


def check_sequence_condition(cond, player_history):
    """
    Проверяет условие типа sequence с полным набором операторов.
    """
    mode = cond.get("mode", "contains")
    seq = normalize_moves(cond.get("moves", []))
    overlapping = cond.get("overlapping", False)

    min_count = cond.get("min")
    max_count = cond.get("max")

    if min_count is not None or max_count is not None:
        count = count_sequence_occurrences(player_history, seq, overlapping=overlapping)
        if min_count is not None and count < min_count:
            return False
        if max_count is not None and count > max_count:
            return False
        return True

    if "operator" in cond or "count" in cond:
        operator = cond.get("operator", ">=")
        count = cond.get("count", 1)
        op_func = get_operator(operator, ">=")
        return op_func(count_sequence_occurrences(player_history, seq, overlapping=overlapping), count)

    if "any" in cond:
        return any(check_sequence_match(player_history, normalize_moves(s), mode, cond.get("count", 1))
                   for s in cond["any"])

    if "all" in cond:
        return all(check_sequence_match(player_history, normalize_moves(s), mode, cond.get("count", 1))
                   for s in cond["all"])

    return check_sequence_match(player_history, seq, mode, cond.get("count", 1))


def format_sequence_requirement(cond):
    mode = cond.get("mode", "contains")
    count = cond.get("count", 1)
    operator = cond.get("operator", ">=")
    min_c = cond.get("min")
    max_c = cond.get("max")

    mode_symbols = {
        "contains": "∋",
        "exact": "≡",
        "starts_with": "⇒",
        "ends_with": "⇐",
        "not_contains": "∌"
    }
    symbol = mode_symbols.get(mode, "")

    def format_moves(moves_spec):
        moves = normalize_moves(moves_spec)
        arrows = {"u": "↑", "d": "↓", "l": "←", "r": "→"}
        return "".join(arrows.get(m, m) for m in moves)

    def format_count_suffix():
        """Формирует суффикс с количеством."""
        if mode in ["exact", "starts_with", "ends_with", "not_contains"]:
            return ""

        if min_c is not None and max_c is not None:
            return f" ×{min_c}-{max_c}"
        elif min_c is not None:
            return f" ×≥{min_c}"
        elif max_c is not None:
            return f" ×≤{max_c}"
        elif count != 1 or operator != ">=":
            op_sym = OP_SYMBOLS.get(operator, operator)
            return f" ×{op_sym}{count}"
        return ""

    suffix = format_count_suffix()

    if "any" in cond:
        seqs = [format_moves(s) for s in cond["any"]]
        return f"{symbol}({'/'.join(seqs)}){suffix}"
    elif "all" in cond:
        seqs = [format_moves(s) for s in cond["all"]]
        return f"{symbol}[{'&'.join(seqs)}]{suffix}"
    else:
        seq = format_moves(cond.get("moves", ""))
        return f"{symbol}{seq}{suffix}"
