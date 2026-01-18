def calculate_target_pos(start, ans_str, cols, rows):
    x, y = start
    mapping = {"u": (0, -1), "d": (0, 1), "l": (-1, 0), "r": (1, 0)}
    for move in ans_str.lower().split():
        if move[0] in mapping:
            dx, dy = mapping[move[0]]
            if 0 <= x + dx < cols and 0 <= y + dy < rows:
                x, y = x + dx, y + dy
    return (x, y)


def normalize_ans(ans_str):
    mapping = {"up": "u", "u": "u", "down": "d", "d": "d", "left": "l", "l": "l", "right": "r", "r": "r"}
    return [mapping[m] for m in ans_str.lower().split() if m in mapping]
