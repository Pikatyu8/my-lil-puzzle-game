import pygame

COLOR_MOVABLE = (255, 165, 0)
COLOR_MOVABLE_BORDER = (200, 130, 0)
COLOR_BLOCKED_MARK = (255, 50, 50)
COLOR_GROUP_LINK = (180, 120, 40)


def dim_color(color, factor=0.4):
    """
    Затемняет цвет, сохраняя его оттенок.
    Factor: 1.0 = оригинал, 0.5 = в два раза темнее, 0.0 = черный.
    Игнорирует alpha, возвращает (R, G, B).
    """
    r, g, b = color[:3]
    return (
        max(0, int(r * factor)),
        max(0, int(g * factor)),
        max(0, int(b * factor))
    )


def _are_neighbors(pos1, pos2):
    """Проверяет, являются ли позиции соседями (по горизонтали/вертикали)."""
    dx = abs(pos1[0] - pos2[0])
    dy = abs(pos1[1] - pos2[1])
    return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)


def draw_movable_objects(surface, manager, cell_size, dim=False):
    """
    Отрисовывает все movable объекты.
    """
    if manager.is_empty():
        return

    factor = 0.4 if dim else 1.0

    c_movable = dim_color(COLOR_MOVABLE, factor)
    c_border = dim_color(COLOR_MOVABLE_BORDER, factor)
    c_mark = dim_color(COLOR_BLOCKED_MARK, factor)
    c_link = dim_color(COLOR_GROUP_LINK, factor)

    groups = manager.get_groups()

    for group_id, positions in groups.items():
        if len(positions) > 1:
            for i, pos1 in enumerate(positions):
                for pos2 in positions[i+1:]:
                    if _are_neighbors(pos1, pos2):
                        x1 = pos1[0] * cell_size + cell_size // 2
                        y1 = pos1[1] * cell_size + cell_size // 2
                        x2 = pos2[0] * cell_size + cell_size // 2
                        y2 = pos2[1] * cell_size + cell_size // 2
                        pygame.draw.line(surface, c_link, (x1, y1), (x2, y2), 4)

    for pos in manager.get_all_positions():
        x, y = pos
        px = x * cell_size + cell_size // 2
        py = y * cell_size + cell_size // 2

        obj = manager.get_at(pos)
        size = int(cell_size * 0.7)
        half = size // 2

        rect = pygame.Rect(px - half, py - half, size, size)
        pygame.draw.rect(surface, c_movable, rect)

        border_width = 4 if (obj and not obj.can_be_pushed_by) else 2
        pygame.draw.rect(surface, c_border, rect, border_width)

        if obj:
            if obj.group_id is not None:
                indicator_r = size // 6
                indicator_x = px + half - indicator_r - 2
                indicator_y = py - half + indicator_r + 2
                pygame.draw.circle(surface, c_link,
                                   (indicator_x, indicator_y), indicator_r)

            mark_len = size // 3
            mark_thick = 3

            if 'up' in obj.blocked:
                pygame.draw.rect(surface, c_mark,
                                 (px - mark_len//2, py - half - mark_thick, mark_len, mark_thick))
            if 'down' in obj.blocked:
                pygame.draw.rect(surface, c_mark,
                                 (px - mark_len//2, py + half, mark_len, mark_thick))
            if 'left' in obj.blocked:
                pygame.draw.rect(surface, c_mark,
                                 (px - half - mark_thick, py - mark_len//2, mark_thick, mark_len))
            if 'right' in obj.blocked:
                pygame.draw.rect(surface, c_mark,
                                 (px + half, py - mark_len//2, mark_thick, mark_len))

            if not obj.can_push:
                cross_size = size // 4
                pygame.draw.line(surface, c_border,
                                 (px - cross_size, py - cross_size),
                                 (px + cross_size, py + cross_size), 2)
                pygame.draw.line(surface, c_border,
                                 (px + cross_size, py - cross_size),
                                 (px - cross_size, py + cross_size), 2)
