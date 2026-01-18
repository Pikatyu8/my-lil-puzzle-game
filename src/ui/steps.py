from src.core import config
from src.ui.fonts import get_font


def draw_step_numbers(surface, path_positions, cell_size):
    cell_data = {}
    for step, pos in enumerate(path_positions):
        if pos not in cell_data:
            cell_data[pos] = []
        if len(cell_data[pos]) < 9:
            cell_data[pos].append(step)
    for pos, steps in cell_data.items():
        for i, val in enumerate(steps):
            f = get_font(max(8, cell_size // 7)) if val >= 100 else get_font(max(10, cell_size // 5))
            ts = f.render(str(val), True, config.COLOR_TEXT)
            surface.blit(ts, (pos[0] * cell_size + 2 + (i % 3) * (cell_size // 3),
                              pos[1] * cell_size + 2 + (i // 3) * (cell_size // 3)))
