import pygame

from src.core import config
from src.utils.misc import dim_color


def draw_player(surface, player_pos, cell_size, dim=False):
    """Отрисовывает игрока. Если dim=True, цвет затемняется."""
    px = player_pos[0] * cell_size + cell_size // 2
    py = player_pos[1] * cell_size + cell_size // 2
    radius = int(cell_size * 0.4)

    color = dim_color(config.COLOR_PLAYER, 0.4) if dim else config.COLOR_PLAYER

    pygame.draw.circle(surface, color, (px, py), radius)

    if dim:
        pygame.draw.circle(surface, (80, 80, 80), (px, py), radius, 1)
