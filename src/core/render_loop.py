import pygame

from src.core import config
from src.movable.render import draw_movable_objects
from src.ui.fonts import get_font
from src.ui.grid import draw_barriers, draw_grid
from src.ui.player import draw_player
from src.ui.requirements import (
    draw_editor_indicator,
    draw_global_requirements,
    draw_requirements,
)
from src.ui.steps import draw_step_numbers


def render_frame(state):
    screen = state["screen"]
    game_surface = state["game_surface"]

    screen.fill(config.COLOR_BG)
    game_surface.fill(config.COLOR_BG)

    is_preview = state["show_requirements"] and (state["level_requirements"] or state["global_requirements"])

    for cell in state["condition_cells"]:
        pygame.draw.rect(game_surface, config.COLOR_CONDITION_HINT,
                         (cell[0] * config.CELL_SIZE, cell[1] * config.CELL_SIZE,
                          config.CELL_SIZE, config.CELL_SIZE))

    if state["target_grid_pos"]:
        pygame.draw.rect(game_surface, config.COLOR_TARGET,
                         (state["target_grid_pos"][0] * config.CELL_SIZE,
                          state["target_grid_pos"][1] * config.CELL_SIZE,
                          config.CELL_SIZE, config.CELL_SIZE))

    draw_grid(game_surface, config.GRID_COLS * config.CELL_SIZE, config.GRID_ROWS * config.CELL_SIZE, config.CELL_SIZE)
    draw_barriers(game_surface, state["walls_data"], config.COLOR_WALL, config.CELL_SIZE)
    draw_barriers(game_surface, state["poison_data"], config.COLOR_POISON, config.CELL_SIZE)

    if not is_preview:
        draw_step_numbers(game_surface, config.path_positions, config.CELL_SIZE)

    draw_movable_objects(game_surface, state["movable_manager"], config.CELL_SIZE, dim=is_preview)
    draw_player(game_surface, state["player_pos"], config.CELL_SIZE, dim=is_preview)

    if state["show_requirements"] and state["level_requirements"]:
        draw_requirements(game_surface, state["level_requirements"], config.CELL_SIZE)

    if config.dev_show_coords:
        f_coords = get_font(max(12, config.CELL_SIZE // 3), bold=True)
        for gy in range(config.GRID_ROWS):
            for gx in range(config.GRID_COLS):
                ts = f_coords.render(f"{gx},{gy}", True, config.COLOR_DEV_COORDS)
                game_surface.blit(ts, ((gx + 1) * config.CELL_SIZE - ts.get_width() - 3,
                                       (gy + 1) * config.CELL_SIZE - ts.get_height() - 3))

    screen.blit(game_surface, (state["grid_offset_x"], state["grid_offset_y"]))

    if state["show_requirements"] and state["global_requirements"]:
        panel_x = config.WINDOW_WIDTH - config.SIDE_PANEL_WIDTH
        draw_global_requirements(
            screen,
            state["global_requirements"],
            get_font(max(12, config.CELL_SIZE // 4), bold=True),
            panel_x
        )

    if config.editor_mode:
        panel_x = config.WINDOW_WIDTH - config.SIDE_PANEL_WIDTH
        draw_editor_indicator(screen, panel_x, config.WINDOW_HEIGHT)

    pygame.display.flip()
