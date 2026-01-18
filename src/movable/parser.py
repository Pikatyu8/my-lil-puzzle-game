from src.movable.manager import MovableManager


def parse_blocked_sides(blocked_raw):
    """Парсит заблокированные стороны."""
    side_map = {
        'u': 'up', 'd': 'down', 'l': 'left', 'r': 'right',
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'
    }

    if not blocked_raw:
        return []

    if isinstance(blocked_raw, str):
        result = []
        for c in blocked_raw.lower():
            if c in side_map:
                result.append(side_map[c])
        return result

    if isinstance(blocked_raw, list):
        result = []
        for b in blocked_raw:
            if isinstance(b, str):
                b_lower = b.lower()
                if b_lower in side_map:
                    result.append(side_map[b_lower])
        return result

    return []


def generate_rect_cells(start, end):
    """Генерирует все клетки в прямоугольнике."""
    x1, y1 = int(start[0]), int(start[1])
    x2, y2 = int(end[0]), int(end[1])
    return [
        (x, y)
        for x in range(min(x1, x2), max(x1, x2) + 1)
        for y in range(min(y1, y2), max(y1, y2) + 1)
    ]


def parse_movable_data(movable_list):
    """
    Парсит данные о movable объектах из JSON.
    """
    manager = MovableManager()

    if not movable_list:
        return manager

    group_counter = 0

    for item in movable_list:
        if not isinstance(item, dict):
            continue

        blocked = parse_blocked_sides(item.get("blocked", []))
        can_push = item.get("can_push", True)
        can_be_pushed_by = item.get("can_be_pushed_by", True)
        connected = item.get("connected", False)

        group_id = None
        if connected:
            group_counter += 1
            group_id = group_counter

        cells = []

        if "cell" in item:
            c = item["cell"]
            cells.append((int(c[0]), int(c[1])))

        if "cells" in item:
            for c in item["cells"]:
                cells.append((int(c[0]), int(c[1])))

        if "range" in item:
            r = item["range"]
            cells.extend(generate_rect_cells(r[0], r[1]))

        if "ranges" in item:
            for r in item["ranges"]:
                cells.extend(generate_rect_cells(r[0], r[1]))

        for cell in cells:
            manager.add_object(cell, blocked, can_push, can_be_pushed_by, group_id)

    return manager
