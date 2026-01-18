def check_poison_on_exit(current_pos, move_dir, poison_data):
    """
    Проверяет, есть ли яд при попытке выйти из клетки (inner barrier).
    Вызывается ПЕРЕД проверкой валидности целевой позиции.
    """
    if not poison_data:
        return False

    for b_pos, b_side, b_type in poison_data:
        if tuple(current_pos) == b_pos and b_side == move_dir and b_type in ["inner", "both"]:
            return True
    return False


def check_poison_on_entry(next_pos, move_dir, poison_data, grid_cols, grid_rows):
    """
    Проверяет, есть ли яд при попытке войти в клетку (outer barrier).
    Также проверяет границы уровня.
    """
    if not poison_data:
        return False

    opposite = {"right": "left", "left": "right", "down": "up", "up": "down"}
    entry_side = opposite.get(move_dir, move_dir)

    nx, ny = next_pos

    if not (0 <= nx < grid_cols and 0 <= ny < grid_rows):
        return False

    for b_pos, b_side, b_type in poison_data:
        if tuple(next_pos) == b_pos and b_side == entry_side and b_type in ["outer", "both"]:
            return True

    return False


def is_path_clear(current_pos, next_pos, barriers_data):
    if not barriers_data:
        return True

    cx, cy = current_pos
    nx, ny = next_pos

    if nx > cx:
        move_dir = "right"
    elif nx < cx:
        move_dir = "left"
    elif ny > cy:
        move_dir = "down"
    elif ny < cy:
        move_dir = "up"
    else:
        return True

    opposite = {"right": "left", "left": "right", "down": "up", "up": "down"}
    entry_side = opposite[move_dir]

    for b_pos, b_side, b_type in barriers_data:
        if tuple(current_pos) == b_pos and b_side == move_dir and b_type in ["inner", "both"]:
            return False
        if tuple(next_pos) == b_pos and b_side == entry_side and b_type in ["outer", "both"]:
            return False
    return True
