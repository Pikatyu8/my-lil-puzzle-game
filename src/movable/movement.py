def try_push_group(manager, group_id, touched_pos, direction, cols, rows,
                   walls_data, poison_data, is_path_clear_func):
    """Пытается толкнуть связанную группу объектов как единое целое."""
    result = {
        'can_move': False,
        'hit_poison': False,
        'blocked_by_wall': False,
        'blocked_by_box': False,
        'out_of_bounds': False,
        'moves_made': [],
        'target_pos': touched_pos
    }

    dx, dy = manager.DIRECTION_DELTA[direction]
    group_positions = manager.get_group_positions(group_id)

    for pos in group_positions:
        new_pos = (pos[0] + dx, pos[1] + dy)

        if not (0 <= new_pos[0] < cols and 0 <= new_pos[1] < rows):
            result['out_of_bounds'] = True
            result['blocked_by_box'] = True
            return result

        if not is_path_clear_func(pos, new_pos, walls_data):
            result['blocked_by_wall'] = True
            result['blocked_by_box'] = True
            return result

        if not is_path_clear_func(pos, new_pos, poison_data):
            result['blocked_by_box'] = True
            return result

        target_obj = manager.get_at(new_pos)
        if target_obj and new_pos not in group_positions:
            result['blocked_by_box'] = True
            return result

    moves = []
    moved_objects = {}

    for pos in group_positions:
        obj = manager.objects.pop(pos)
        new_pos = (pos[0] + dx, pos[1] + dy)
        obj.pos = new_pos
        moved_objects[new_pos] = obj
        moves.append((pos, new_pos))

    manager.objects.update(moved_objects)

    result['can_move'] = True
    result['moves_made'] = moves
    return result


def collect_push_chain(manager, start_pos, direction, cols, rows,
                       walls_data, poison_data, is_path_clear_func):
    """
    Собирает цепочку одиночных объектов для перемещения.
    Группы не могут быть частью цепочки.
    """
    dx, dy = manager.DIRECTION_DELTA[direction]
    chain = []
    current_pos = start_pos
    push_side = manager.OPPOSITE[direction]

    while True:
        obj = manager.get_at(current_pos)
        if not obj:
            break

        if obj.group_id is not None and current_pos != start_pos:
            return None

        chain.append(current_pos)
        next_pos = (current_pos[0] + dx, current_pos[1] + dy)

        if not (0 <= next_pos[0] < cols and 0 <= next_pos[1] < rows):
            return None

        if not is_path_clear_func(current_pos, next_pos, walls_data):
            return None

        if not is_path_clear_func(current_pos, next_pos, poison_data):
            return None

        next_obj = manager.get_at(next_pos)
        if next_obj:
            if next_obj.group_id is not None:
                return None

            if not obj.can_push:
                return None

            if not next_obj.can_be_pushed_by:
                return None

            if push_side in next_obj.blocked:
                return None

        current_pos = next_pos

    return chain if chain else None
