import pygame

from src.core import config
from src.core.level_loader import load_level
from src.core.move_handler import handle_move
from src.data.level_io import process_level_data
from src.editor.reload import reload_edit_level


def handle_keydown(state, event, keys, current_idx, hints_enabled, state_manager, screen_w, screen_h):
    if keys[pygame.K_F9] and keys[pygame.K_F11]:
        config.dev_access_granted = True
        print("\n[DEV] Активировано!\n")

    if event.key == pygame.K_r:
        full_reset = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        load_level(state, current_idx, clear_history=full_reset, screen_w=screen_w,
                   screen_h=screen_h, hints_enabled=hints_enabled, state_manager=state_manager)
        return current_idx, True, True

    if event.key == pygame.K_x:
        state["show_requirements"] = not state["show_requirements"]
        return current_idx, False, True

    if event.key == pygame.K_RETURN and config.editor_mode:
        new_levels = reload_edit_level(process_level_data)
        if new_levels:
            config.LEVELS = new_levels
            current_idx = 0
            load_level(state, current_idx, clear_history=True, screen_w=screen_w,
                       screen_h=screen_h, hints_enabled=hints_enabled, state_manager=state_manager)
        return current_idx, True, True

    if event.key == pygame.K_s:
        movable_state = state["movable_manager"].copy_state()
        state_manager.save_manual(state["player_pos"], config.path_positions, state["player_history"],
                                  config.dev_recording, movable_state)
        return current_idx, False, True

    if event.key == pygame.K_l:
        data = state_manager.load_manual()
        if data:
            state["player_pos"] = data['pos']
            config.path_positions = data['path']
            state["player_history"] = data['hist']
            config.dev_recording = data['dev']
            if 'movable' in data:
                state["movable_manager"].restore_state(data['movable'])
            if len(config.path_positions) > 1:
                state["show_requirements"] = False
        return current_idx, False, True

    if event.key == pygame.K_z:
        data = state_manager.pop()
        if data:
            state["player_pos"] = data['pos']
            config.path_positions = data['path']
            state["player_history"] = data['hist']
            config.dev_recording = data['dev']
            if 'movable' in data:
                state["movable_manager"].restore_state(data['movable'])
            if len(config.path_positions) > 1:
                state["show_requirements"] = False
        else:
            print("[UNDO] История пуста")
        return current_idx, False, True

    move = None
    if event.key == pygame.K_UP:
        move = "u"
    elif event.key == pygame.K_DOWN:
        move = "d"
    elif event.key == pygame.K_LEFT:
        move = "l"
    elif event.key == pygame.K_RIGHT:
        move = "r"

    if move:
        current_idx, needs_reload = handle_move(
            state, move, current_idx, hints_enabled, state_manager, screen_w, screen_h
        )
        return current_idx, needs_reload, True

    return current_idx, False, False
