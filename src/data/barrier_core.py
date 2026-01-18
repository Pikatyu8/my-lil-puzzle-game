SIDE_MAP = {
    'u': 'up', 'd': 'down', 'l': 'left', 'r': 'right',
    'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'
}
ALL_SIDES = ['up', 'down', 'left', 'right']


def parse_sides(sides_str):
    if not sides_str or sides_str in ["all", "box", "square", "lrud", "udlr"]:
        return ALL_SIDES[:]

    result = []
    for c in sides_str.lower():
        if c in SIDE_MAP:
            side = SIDE_MAP[c]
            if side not in result:
                result.append(side)
    return result if result else ALL_SIDES[:]


def generate_rect_cells(start, end):
    x1, y1 = int(start[0]), int(start[1])
    x2, y2 = int(end[0]), int(end[1])
    return [
        (x, y)
        for x in range(min(x1, x2), max(x1, x2) + 1)
        for y in range(min(y1, y2), max(y1, y2) + 1)
    ]


def generate_perimeter(start, end, sides):
    x1 = min(int(start[0]), int(end[0]))
    y1 = min(int(start[1]), int(end[1]))
    x2 = max(int(start[0]), int(end[0]))
    y2 = max(int(start[1]), int(end[1]))

    result = []
    if 'left' in sides:
        result.extend(((x1, y), 'left') for y in range(y1, y2 + 1))
    if 'right' in sides:
        result.extend(((x2, y), 'right') for y in range(y1, y2 + 1))
    if 'up' in sides:
        result.extend(((x, y1), 'up') for x in range(x1, x2 + 1))
    if 'down' in sides:
        result.extend(((x, y2), 'down') for x in range(x1, x2 + 1))
    return result


def is_new_format(item):
    return isinstance(item, dict) and any(
        key in item for key in ["cell", "cells", "range", "ranges", "type", "sides", "mode"]
    )


def is_coord(item):
    return (isinstance(item, list) and len(item) == 2 and
            isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)))
