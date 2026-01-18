from src.core import config


def console_listener():
    print("\n[DEV] Консоль. F9+F11 для активации.")
    while config.game_running:
        try:
            cmd = input().strip().lower()
            if not config.game_running:
                break
            if not config.dev_access_granted:
                print("[LOCKED] F9+F11")
                continue

            if cmd == '1':
                print(f"ans: {' '.join(config.dev_recording)}\n")
            elif cmd == '2':
                config.dev_recording.clear()
                print("[OK] Очищено\n")
            elif cmd == '3':
                config.dev_show_coords = not config.dev_show_coords
                print(f"[OK] Координаты: {'ВКЛ' if config.dev_show_coords else 'ВЫКЛ'}\n")
            elif cmd == '4':
                cell_map = {}
                for step, pos in enumerate(config.path_positions):
                    if pos not in cell_map:
                        cell_map[pos] = []
                    cell_map[pos].append(step)
                print("\n=== КЛЕТКИ ===")
                for cell in sorted(cell_map.keys(), key=lambda k: (k[1], k[0])):
                    print(f"{cell[0]},{cell[1]}: {cell_map[cell]}")
                print("==============\n")
            elif cmd == '5':
                config.dev_disable_victory = not config.dev_disable_victory
                print(f"[OK] Победа: {'ВЫКЛ' if config.dev_disable_victory else 'ВКЛ'}\n")
            elif cmd == 'help':
                print("\n1=SHOW 2=CLEAR 3=COORDS 4=CELLS 5=NOWIN\n")
        except EOFError:
            break
