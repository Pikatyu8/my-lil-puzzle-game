from src.core import config
from src.core.level_loader import load_level
from src.logic.barriers import check_poison_on_entry, check_poison_on_exit, is_path_clear
from src.logic.conditions import check_all_conditions


def handle_move(state, move, current_idx, hints_enabled, state_manager, screen_w, screen_h):
    if state["show_requirements"] and len(config.path_positions) == 1:
        state["show_requirements"] = False

    move_dir = {"u": "up", "d": "down", "l": "left", "r": "right"}[move]

    if check_poison_on_exit(state["player_pos"], move_dir, state["poison_data"]):
        movable_state_before = state["movable_manager"].copy_state()
        state_manager.push(state["player_pos"], config.path_positions, state["player_history"],
                           config.dev_recording, movable_state_before)
        print("☠ ПОГИБ от яда на выходе! (Z = откат, L = загрузка)")
        load_level(state, current_idx, clear_history=False, screen_w=screen_w,
                   screen_h=screen_h, hints_enabled=hints_enabled, state_manager=state_manager)
        return current_idx, True

    movable_state_before = state["movable_manager"].copy_state()

    result = state["movable_manager"].try_push(
        state["player_pos"], move, config.GRID_COLS, config.GRID_ROWS,
        state["walls_data"], state["poison_data"], is_path_clear
    )

    if result['hit_poison']:
        state_manager.push(state["player_pos"], config.path_positions, state["player_history"],
                           config.dev_recording, movable_state_before)
        print("☠ ПОГИБ! (Z = откат, L = загрузка)")
        load_level(state, current_idx, clear_history=False, screen_w=screen_w,
                   screen_h=screen_h, hints_enabled=hints_enabled, state_manager=state_manager)
        return current_idx, True

    if result['can_move']:
        target = result['target_pos']
        if check_poison_on_entry(target, move_dir, state["poison_data"], config.GRID_COLS, config.GRID_ROWS):
            state_manager.push(state["player_pos"], config.path_positions, state["player_history"],
                               config.dev_recording, movable_state_before)
            print("☠ ПОГИБ от яда на входе! (Z = откат, L = загрузка)")
            load_level(state, current_idx, clear_history=False, screen_w=screen_w,
                       screen_h=screen_h, hints_enabled=hints_enabled, state_manager=state_manager)
            return current_idx, True

        state_manager.push(state["player_pos"], config.path_positions, state["player_history"],
                           config.dev_recording, movable_state_before)

        state["player_pos"] = list(result['target_pos'])

        if result['moves_made']:
            print(f"[BOX] Сдвинуто: {len(result['moves_made'])} объектов")

    state["player_history"].append(move)
    config.dev_recording.append(move)
    config.path_positions.append(tuple(state["player_pos"]))

    if check_all_conditions(state["level_conditions"], config.path_positions,
                            state["player_pos"], config.GRID_COLS, config.GRID_ROWS,
                            state["player_history"]):
        if config.dev_disable_victory:
            print("[DEV] Победа OFF")
        else:
            print(f"✓ Уровень {current_idx + 1} пройден!")

            if config.editor_mode:
                print("[EDITOR] Пройдено! R = сброс, Enter = перезагрузка файла")
            else:
                current_idx += 1
                if current_idx < len(config.LEVELS):
                    load_level(state, current_idx, clear_history=True, screen_w=screen_w,
                               screen_h=screen_h, hints_enabled=hints_enabled, state_manager=state_manager)
                    return current_idx, True
                else:
                    print("\n🎉 ИГРА ПРОЙДЕНА! 🎉")
                    config.game_running = False

    return current_idx, False
