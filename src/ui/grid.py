import pygame

from src.core import config


def draw_grid(surface, width, height, cell_size):
    for x in range(0, width + 1, cell_size):
        pygame.draw.line(surface, config.COLOR_GRID, (x, 0), (x, height))
    for y in range(0, height + 1, cell_size):
        pygame.draw.line(surface, config.COLOR_GRID, (0, y), (width, y))


def draw_barriers(surface, barriers_data, color, cell_size):
    if not barriers_data:
        return
    for b_pos, side, b_type in barriers_data:
        px, py = b_pos
        x, y = px * cell_size, py * cell_size

        if side == "up":
            start, end = (x, y), (x + cell_size, y)
        elif side == "down":
            start, end = (x, y + cell_size), (x + cell_size, y + cell_size)
        elif side == "left":
            start, end = (x, y), (x, y + cell_size)
        elif side == "right":
            start, end = (x + cell_size, y), (x + cell_size, y + cell_size)
        else:
            continue

        pygame.draw.line(surface, color, start, end, 5 if b_type == "both" else 3)

        if b_type != "both":
            mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            offset = 6
            if side == "up":
                dy = -offset if b_type == "outer" else offset
                pts = [(mid_x, mid_y + dy), (mid_x - 4, mid_y), (mid_x + 4, mid_y)]
            elif side == "down":
                dy = offset if b_type == "outer" else -offset
                pts = [(mid_x, mid_y + dy), (mid_x - 4, mid_y), (mid_x + 4, mid_y)]
            elif side == "left":
                dx = -offset if b_type == "outer" else offset
                pts = [(mid_x + dx, mid_y), (mid_x, mid_y - 4), (mid_x, mid_y + 4)]
            elif side == "right":
                dx = offset if b_type == "outer" else -offset
                pts = [(mid_x + dx, mid_y), (mid_x, mid_y - 4), (mid_x, mid_y + 4)]
            pygame.draw.polygon(surface, color, pts)
