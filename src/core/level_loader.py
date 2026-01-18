import pygame

from src.core import config
from src.logic.answers import calculate_target_pos
from src.logic.requirements import get_condition_cells, get_condition_requirements
from src.movable.parser import parse_movable_data


def load_level(state, idx, clear_history, screen_w, screen_h, hints_enabled, state_manager):
    lvl = config.LEVELS[idx]
    config.GRID_COLS, config.GRID_ROWS = lvl.get("grid", (16, 12))

    available_w = (screen_w * 0.85) - config.SIDE_PANEL_WIDTH
    max_h = screen_h * 0.85

    config.CELL_SIZE = int(min(available_w // config.GRID_COLS, max_h // config.GRID_ROWS))

    grid_w, grid_h = config.CELL_SIZE * config.GRID_COLS, config.CELL_SIZE * config.GRID_ROWS
    state["grid_offset_x"] = int(grid_w * 0.05)
    state["grid_offset_y"] = int(grid_h * 0.05)

    config.WINDOW_WIDTH = grid_w + state["grid_offset_x"] * 2 + config.SIDE_PANEL_WIDTH
    config.WINDOW_HEIGHT = grid_h + state["grid_offset_y"] * 2

    state["screen"] = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    state["game_surface"] = pygame.Surface((grid_w + 1, grid_h + 1), pygame.SRCALPHA)

    state["player_pos"] = list(lvl["start"])
    state["player_history"] = []
    config.dev_recording.clear()
    config.path_positions = [tuple(state["player_pos"])]

    if clear_history:
        state_manager.reset()
        print("[RESET] Полный сброс (история очищена)")
    else:
        print(f"[RESET] Мягкий сброс (Z/L доступны, история: {len(state_manager.history)})")

    state["poison_data"] = lvl.get("poison", [])[:]
    state["walls_data"] = lvl.get("walls", [])[:]

    if "movable" in lvl:
        state["movable_manager"] = parse_movable_data(lvl.get("movable", []))
    else:
        state["movable_manager"].clear()

    if lvl.get("wall_is_poison"):
        flag = lvl["wall_is_poison"]
        exceptions = [tuple(c) for c in flag.get("except", [])] if isinstance(flag, dict) else []
        new_walls = []
        for w in state["walls_data"]:
            if w[0] not in exceptions:
                state["poison_data"].append(w)
            else:
                new_walls.append(w)
        state["walls_data"] = new_walls

    state["show_requirements"] = True
    state["level_requirements"], state["global_requirements"] = get_condition_requirements(
        lvl, config.GRID_COLS, config.GRID_ROWS
    )

    state["level_conditions"] = lvl.get("conditions", [])
    state["condition_cells"] = get_condition_cells(lvl, config.GRID_COLS, config.GRID_ROWS)

    if lvl.get("type") == "sequence" and "ans" in lvl:
        ans_moves = lvl.get("ans", "")
        state["target_grid_pos"] = calculate_target_pos(
            lvl["start"], ans_moves, config.GRID_COLS, config.GRID_ROWS
        )
        if not any(c.get("check") == "sequence" for c in state["level_conditions"]):
            state["level_conditions"].append({
                "check": "sequence",
                "moves": ans_moves,
                "mode": "exact"
            })
        if not any(c.get("check") == "end_at" for c in state["level_conditions"]):
            state["level_conditions"].append({
                "check": "end_at",
                "cells": [list(state["target_grid_pos"])]
            })
    else:
        state["target_grid_pos"] = None

    name = lvl.get("name", f"Уровень {idx + 1}")
    mode_prefix = "[EDIT] " if config.editor_mode else ""
    pygame.display.set_caption(f"{mode_prefix}{name} ({config.GRID_COLS}x{config.GRID_ROWS})")
    print(f"\n{'='*40}\n--- {mode_prefix}{name} ---")
    if hints_enabled and "hint" in lvl:
        print(f"Подсказка: {lvl['hint']}")
    print(f"{'='*40}\n")
