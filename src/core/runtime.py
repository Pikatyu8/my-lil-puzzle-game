import sys
import threading

import pygame

from src.core import config
from src.core.console import console_listener
from src.core.input_handler import handle_keydown
from src.core.level_loader import load_level
from src.core.render_loop import render_frame
from src.movable.manager import MovableManager
from src.savestates import StateManager


def run_game(selected_idx, hints_enabled, edit_mode_enabled=False):
    config.editor_mode = edit_mode_enabled

    if not config.LEVELS:
        print("[CRITICAL] Нет уровней.")
        sys.exit(1)

    pygame.init()
    pygame.font.init()

    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    current_idx = selected_idx
    clock = pygame.time.Clock()

    state = {
        "screen": None,
        "game_surface": None,
        "grid_offset_x": 0,
        "grid_offset_y": 0,
        "player_pos": [0, 0],
        "player_history": [],
        "target_grid_pos": None,
        "level_conditions": [],
        "condition_cells": [],
        "poison_data": [],
        "walls_data": [],
        "show_requirements": True,
        "level_requirements": {},
        "global_requirements": [],
        "movable_manager": MovableManager(),
    }

    state_manager = StateManager(max_history=200)

    console_thread = threading.Thread(target=console_listener, daemon=True)
    console_thread.start()

    def reload_fonts():
        pass

    load_level(state, current_idx, clear_history=True, screen_w=screen_w,
               screen_h=screen_h, hints_enabled=hints_enabled, state_manager=state_manager)
    reload_fonts()

    while config.game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                config.game_running = False

            if event.type == pygame.KEYDOWN:
                keys = pygame.key.get_pressed()
                current_idx, needs_reload, handled = handle_keydown(
                    state, event, keys, current_idx, hints_enabled, state_manager, screen_w, screen_h
                )
                if needs_reload:
                    reload_fonts()
                if handled:
                    continue

        render_frame(state)
        clock.tick(60)

    pygame.quit()
    sys.exit()
