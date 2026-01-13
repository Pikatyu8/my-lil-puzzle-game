import pygame
import sys
import threading
import json
import os

# --- ЦВЕТА ---
COLOR_BG = (0, 0, 0)
COLOR_GRID = (255, 255, 255)
COLOR_PLAYER = (255, 255, 255)
COLOR_TARGET = (64, 64, 64)
COLOR_TEXT = (150, 150, 150)
COLOR_DEV_COORDS = (255, 165, 0)
COLOR_CONDITION_HINT = (40, 60, 40)

# Новые цвета
COLOR_POISON = (255, 50, 50)     # Красный (смерть)
COLOR_WALL = (128, 255, 176)     # #80FFB0 (блокада)

# Глобальные переменные
dev_recording = []
path_positions = []  # Теперь глобально, чтобы видеть из консоли
game_running = True
dev_access_granted = False
dev_show_coords = False

# Динамические размеры
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 50
GRID_COLS = 16
GRID_ROWS = 12

# =============================================================================
# РАБОТА С ФАЙЛАМИ И JSON
# =============================================================================

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_levels():
    path = resource_path("levels.json")
    
    if not os.path.exists(path):
        print(f"[ERROR] Файл уровней не найден: {path}")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for lvl in data:
            if "grid" in lvl: lvl["grid"] = tuple(lvl["grid"])
            if "start" in lvl: lvl["start"] = tuple(lvl["start"])
            
            if "conditions" in lvl:
                for cond in lvl["conditions"]:
                    if "cells" in cond and isinstance(cond["cells"], list):
                        cond["cells"] = [tuple(c) for c in cond["cells"]]
            
            # Обработка списков барьеров (poison и walls)
            for key in ["poison", "walls"]:
                if key in lvl:
                    processed = []
                    for item in lvl[key]:
                        processed.append((tuple(item[0]), item[1], item[2]))
                    lvl[key] = processed
                        
        return data
    except Exception as e:
        print(f"[ERROR] Ошибка чтения JSON: {e}")
        sys.exit(1)

LEVELS = load_levels()

# =============================================================================
# ЛОГИКА ИГРЫ И ПРОВЕРКИ
# =============================================================================

def resolve_cells(cells_spec, grid_cols, grid_rows):
    if isinstance(cells_spec, list): return cells_spec
    if cells_spec == "corners":
        return [(0, 0), (grid_cols - 1, 0), (0, grid_rows - 1), (grid_cols - 1, grid_rows - 1)]
    elif cells_spec == "edges":
        edges = set()
        for x in range(grid_cols): edges.add((x, 0)); edges.add((x, grid_rows - 1))
        for y in range(grid_rows): edges.add((0, y)); edges.add((grid_cols - 1, y))
        return list(edges)
    elif cells_spec == "center":
        return [(grid_cols // 2, grid_rows // 2)]
    return []

def check_condition(condition, path_positions, player_pos, grid_cols, grid_rows):
    check_type = condition.get("check", "")
    if check_type == "cell_has_steps":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        match_mode = condition.get("match", "any")
        required_steps = set(condition.get("required_steps", []))
        cell_steps = {}
        for step_num, pos in enumerate(path_positions):
            if pos not in cell_steps: cell_steps[pos] = set()
            cell_steps[pos].add(step_num)
        
        if match_mode == "any":
            for cell in cells:
                if cell in cell_steps and required_steps.issubset(cell_steps[cell]): return True
            return False
        else:
            for cell in cells:
                if cell not in cell_steps or not required_steps.issubset(cell_steps[cell]): return False
            return True
    elif check_type == "visit_cells":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        match_mode = condition.get("match", "any")
        visited = set(path_positions)
        if match_mode == "any": return bool(visited & set(cells))
        else: return set(cells).issubset(visited)
    elif check_type == "total_steps":
        required = condition.get("count", 0)
        operator = condition.get("operator", "==")
        actual = len(path_positions) - 1
        ops = {"==": lambda a, b: a == b, ">=": lambda a, b: a >= b, 
               "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}
        return ops.get(operator, lambda a, b: False)(actual, required)
    elif check_type == "end_at":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        return tuple(player_pos) in cells
    return False

def check_all_conditions(conditions, path_positions, player_pos, grid_cols, grid_rows):
    for cond in conditions:
        if not check_condition(cond, path_positions, player_pos, grid_cols, grid_rows):
            return False
    return True

def get_condition_cells(level_data, grid_cols, grid_rows):
    if level_data.get("type") != "condition": return []
    cells = set()
    for cond in level_data.get("conditions", []):
        if "cells" in cond:
            cells.update(resolve_cells(cond["cells"], grid_cols, grid_rows))
    return list(cells)

# --- ЛОГИКА БАРЬЕРОВ (Стены и Яд) ---

def is_path_clear(current_pos, next_pos, barriers_data):
    if not barriers_data:
        return True

    cx, cy = current_pos
    nx, ny = next_pos
    
    move_dir = ""
    if nx > cx: move_dir = "right"
    elif nx < cx: move_dir = "left"
    elif ny > cy: move_dir = "down"
    elif ny < cy: move_dir = "up"
    
    opposite_dir = {"right": "left", "left": "right", "down": "up", "up": "down"}
    entry_side = opposite_dir.get(move_dir)

    for b_pos, b_side, b_type in barriers_data:
        # 1. Проверка ВЫХОДА из текущей клетки
        if tuple(current_pos) == b_pos and b_side == move_dir:
            if b_type in ["inner", "both"]:
                return False

        # 2. Проверка ВХОДА в следующую клетку
        if tuple(next_pos) == b_pos and b_side == entry_side:
            if b_type in ["outer", "both"]:
                return False
                
    return True

# =============================================================================
# ОТРИСОВКА
# =============================================================================

def draw_barriers(surface, barriers_data, color, cell_size):
    if not barriers_data:
        return

    for b_pos, side, b_type in barriers_data:
        px, py = b_pos
        x = px * cell_size
        y = py * cell_size
        
        start_pos, end_pos = (0,0), (0,0)
        if side == "up": start_pos, end_pos = (x, y), (x + cell_size, y)
        elif side == "down": start_pos, end_pos = (x, y + cell_size), (x + cell_size, y + cell_size)
        elif side == "left": start_pos, end_pos = (x, y), (x, y + cell_size)
        elif side == "right": start_pos, end_pos = (x + cell_size, y), (x + cell_size, y + cell_size)

        line_width = 5 if b_type == "both" else 3
        pygame.draw.line(surface, color, start_pos, end_pos, line_width)

        if b_type != "both":
            mid_x = (start_pos[0] + end_pos[0]) / 2
            mid_y = (start_pos[1] + end_pos[1]) / 2
            offset = 6
            p1, p2, p3 = (0,0), (0,0), (0,0)

            if side == "up":
                dy = -offset if b_type == "outer" else offset
                p1 = (mid_x, mid_y + dy); p2 = (mid_x - 4, mid_y); p3 = (mid_x + 4, mid_y)
            elif side == "down":
                dy = offset if b_type == "outer" else -offset
                p1 = (mid_x, mid_y + dy); p2 = (mid_x - 4, mid_y); p3 = (mid_x + 4, mid_y)
            elif side == "left":
                dx = -offset if b_type == "outer" else offset
                p1 = (mid_x + dx, mid_y); p2 = (mid_x, mid_y - 4); p3 = (mid_x, mid_y + 4)
            elif side == "right":
                dx = offset if b_type == "outer" else -offset
                p1 = (mid_x + dx, mid_y); p2 = (mid_x, mid_y - 4); p3 = (mid_x, mid_y + 4)
            
            pygame.draw.polygon(surface, color, [p1, p2, p3])

def calculate_target_pos(start_pos, ans_str, grid_cols, grid_rows):
    x, y = start_pos
    mapping = {"u": (0, -1), "d": (0, 1), "l": (-1, 0), "r": (1, 0)}
    for move in ans_str.lower().split():
        m = move[0]
        if m in mapping:
            dx, dy = mapping[m]
            if 0 <= x + dx < grid_cols and 0 <= y + dy < grid_rows:
                x += dx; y += dy
    return (x, y)

def normalize_ans(ans_str):
    mapping = {"up": "u", "u": "u", "down": "d", "d": "d", "left": "l", "l": "l", "right": "r", "r": "r"}
    return [mapping[move] for move in ans_str.lower().split() if move in mapping]

def draw_grid(surface, width, height, cell_size):
    for x in range(0, width, cell_size): pygame.draw.line(surface, COLOR_GRID, (x, 0), (x, height))
    for y in range(0, height, cell_size): pygame.draw.line(surface, COLOR_GRID, (0, y), (width, y))

# =============================================================================
# РАЗРАБОТЧИК
# =============================================================================
def console_listener():
    print("\n[DEV SYSTEM] Консоль запущена. F9+F11 для разблокировки.")
    while game_running:
        try:
            command = input()
            if not game_running: break
            if not dev_access_granted:
                print("[LOCKED] Активируйте режим разработчика (F9+F11).")
                continue
            cmd_clean = command.strip().lower()
            if cmd_clean == '1': 
                print(f"ans: {' '.join(dev_recording)}\n")
            elif cmd_clean == '2': 
                dev_recording.clear()
                print("[INFO] Очищено.\n")
            elif cmd_clean == '3':
                global dev_show_coords
                dev_show_coords = not dev_show_coords
                print(f"[INFO] Координаты: {'ВКЛ' if dev_show_coords else 'ВЫКЛ'}\n")
            elif cmd_clean == '4' or cmd_clean == 'cells':
                # Вывод: (x, y): [step1, step2, ...]
                cell_map = {}
                for step, pos in enumerate(path_positions):
                    if pos not in cell_map: cell_map[pos] = []
                    cell_map[pos].append(step)
                
                print("\n=== ДАННЫЕ ПО КЛЕТКАМ ===")
                # Сортировка по Y, затем по X для удобства чтения
                sorted_cells = sorted(cell_map.keys(), key=lambda k: (k[1], k[0]))
                for cell in sorted_cells:
                    print(f"{cell[0]},{cell[1]}: {cell_map[cell]}")
                print("=========================\n")
            elif cmd_clean == 'help': 
                print_menu()
            else: 
                print("Неизвестная команда.")
        except EOFError: break

def print_menu():
    print("\n=== DEV МЕНЮ ===\n1. SHOW | 2. CLEAR | 3. COORDS | 4. CELLS | help\n================")

# =============================================================================
# ОСНОВНОЙ ЦИКЛ
# =============================================================================

def run_game(selected_idx, hints_enabled):
    global game_running, dev_recording, dev_access_granted, path_positions
    global WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS

    pygame.init()
    pygame.font.init()

    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    current_idx = selected_idx
    screen = None
    clock = pygame.time.Clock()

    player_pos = [0, 0]
    required_sequence = []
    player_history = []
    path_positions = [] # Инициализация
    target_grid_pos = None
    level_type = "sequence"
    level_conditions = []
    condition_cells = []
    
    poison_data = [] 
    walls_data = []

    console_thread = threading.Thread(target=console_listener, daemon=True)
    console_thread.start()

    def load_level_data(idx):
        nonlocal player_pos, required_sequence, player_history, target_grid_pos
        nonlocal level_type, level_conditions, condition_cells, poison_data, walls_data, screen
        global dev_recording, path_positions
        global WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS

        level_data = LEVELS[idx]
        GRID_COLS, GRID_ROWS = level_data.get("grid", (16, 12))
        
        max_w = screen_w * 0.9
        max_h = screen_h * 0.9
        CELL_SIZE = int(min(max_w // GRID_COLS, max_h // GRID_ROWS))
        WINDOW_WIDTH = CELL_SIZE * GRID_COLS
        WINDOW_HEIGHT = CELL_SIZE * GRID_ROWS
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        
        level_type = level_data.get("type", "sequence")
        start = level_data["start"]
        player_pos = list(start)
        player_history = []
        dev_recording.clear()
        path_positions = [tuple(player_pos)] # Сброс и добавление старта
        
        poison_data = level_data.get("poison", [])
        walls_data = level_data.get("walls", [])
        
        if level_type == "sequence":
            required_sequence = normalize_ans(level_data.get("ans", ""))
            target_grid_pos = calculate_target_pos(start, level_data.get("ans", ""), GRID_COLS, GRID_ROWS)
            level_conditions = []
            condition_cells = []
        else:
            required_sequence = []
            target_grid_pos = None
            level_conditions = level_data.get("conditions", [])
            condition_cells = get_condition_cells(level_data, GRID_COLS, GRID_ROWS)
        
        name = level_data.get("name", f"Уровень {idx + 1}")
        pygame.display.set_caption(f"{name} ({GRID_COLS}x{GRID_ROWS})")
        
        print(f"\n{'='*50}\n--- {name} ---\nТип: {level_type}")
        if hints_enabled and "hint" in level_data: print(f"Подсказка: {level_data['hint']}")
        if walls_data: print(f"Стены (зеленые): {len(walls_data)}")
        if poison_data: print(f"Яд (красные): {len(poison_data)}")
        print(f"{'='*50}\n")

    load_level_data(current_idx)
    
    # Инициализация двух шрифтов
    font_steps = pygame.font.SysFont("Arial", max(10, CELL_SIZE // 4))
    font_steps_small = pygame.font.SysFont("Arial", max(8, CELL_SIZE // 5)) # Чуть меньше для 3 цифр
    font_coords = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 3), bold=True)

    while game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: game_running = False
            
            if event.type == pygame.KEYDOWN:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_F9] and keys[pygame.K_F11]:
                    dev_access_granted = True; print_menu()

                if event.key == pygame.K_r:
                    load_level_data(current_idx)
                    font_steps = pygame.font.SysFont("Arial", max(10, CELL_SIZE // 4))
                    font_steps_small = pygame.font.SysFont("Arial", max(8, CELL_SIZE // 5))
                    font_coords = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 3), bold=True)
                    continue

                # --- ЛОГИКА ДВИЖЕНИЯ ---
                move_attempt = None
                dx, dy = 0, 0
                
                if event.key == pygame.K_UP:    dx, dy = 0, -1; move_attempt = "u"
                elif event.key == pygame.K_DOWN:  dx, dy = 0, 1;  move_attempt = "d"
                elif event.key == pygame.K_LEFT:  dx, dy = -1, 0; move_attempt = "l"
                elif event.key == pygame.K_RIGHT: dx, dy = 1, 0;  move_attempt = "r"

                if move_attempt:
                    target_pos = [player_pos[0] + dx, player_pos[1] + dy]
                    
                    # 1. Проверка границ
                    in_bounds = (0 <= target_pos[0] < GRID_COLS and 0 <= target_pos[1] < GRID_ROWS)
                    
                    # 2. Проверка Стен (Зеленые)
                    blocked_by_wall = False
                    if in_bounds:
                        if not is_path_clear(player_pos, target_pos, walls_data):
                            blocked_by_wall = True

                    # 3. Проверка Яда (Красные)
                    hit_poison = False
                    if in_bounds and not blocked_by_wall:
                        if not is_path_clear(player_pos, target_pos, poison_data):
                            hit_poison = True
                    
                    # ЛОГИКА СМЕРТИ
                    if hit_poison:
                        print("☠ ВЫ ПОГИБЛИ! (Задели ядовитый барьер)")
                        load_level_data(current_idx)
                        continue

                    # ЛОГИКА ПЕРЕМЕЩЕНИЯ
                    if not in_bounds or blocked_by_wall:
                        # Стоим на месте, но считаем шаг
                        pass 
                    else:
                        player_pos = target_pos

                    # ЗАПИСЬ ШАГА
                    player_history.append(move_attempt)
                    dev_recording.append(move_attempt)
                    path_positions.append(tuple(player_pos))

                    # ПРОВЕРКА ПОБЕДЫ
                    level_complete = False
                    if level_type == "sequence":
                        if player_history == required_sequence: level_complete = True
                        elif len(player_history) >= len(required_sequence):
                             if hints_enabled: print("Неверная последовательность! Жмите 'R'.")
                    else:
                        if check_all_conditions(level_conditions, path_positions, player_pos, GRID_COLS, GRID_ROWS):
                            level_complete = True
                    
                    if level_complete:
                        print(f"✓ Уровень {current_idx + 1} ПРОЙДЕН!")
                        current_idx += 1
                        if current_idx < len(LEVELS):
                            load_level_data(current_idx)
                            font_steps = pygame.font.SysFont("Arial", max(10, CELL_SIZE // 4))
                            font_steps_small = pygame.font.SysFont("Arial", max(8, CELL_SIZE // 5))
                            font_coords = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 3), bold=True)
                        else:
                            print("\n🎉 ВЫ ПРОШЛИ ВСЮ ИГРУ! 🎉")
                            game_running = False

        screen.fill(COLOR_BG)
        
        if level_type == "sequence" and target_grid_pos:
            pygame.draw.rect(screen, COLOR_TARGET, (target_grid_pos[0]*CELL_SIZE, target_grid_pos[1]*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        
        if level_type == "condition":
            for cell in condition_cells:
                pygame.draw.rect(screen, COLOR_CONDITION_HINT, (cell[0]*CELL_SIZE, cell[1]*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        
        # Отрисовка шагов
        cell_data = {}
        for step_num, pos in enumerate(path_positions):
            if pos not in cell_data: cell_data[pos] = []
            if len(cell_data[pos]) < 9: cell_data[pos].append(step_num)
        
        for pos, steps in cell_data.items():
            for i, val in enumerate(steps):
                # Выбор шрифта: маленький для 3 цифр (>= 100), обычный для остальных
                current_font = font_steps_small if val >= 100 else font_steps
                
                txt_surf = current_font.render(str(val), True, COLOR_TEXT)
                screen.blit(txt_surf, (pos[0]*CELL_SIZE+2+(i%3)*(CELL_SIZE//3), pos[1]*CELL_SIZE+2+(i//3)*(CELL_SIZE//3)))

        draw_grid(screen, WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE)
        
        draw_barriers(screen, walls_data, COLOR_WALL, CELL_SIZE)
        draw_barriers(screen, poison_data, COLOR_POISON, CELL_SIZE)

        px, py = player_pos[0]*CELL_SIZE + CELL_SIZE//2, player_pos[1]*CELL_SIZE + CELL_SIZE//2
        pygame.draw.circle(screen, COLOR_PLAYER, (px, py), int(CELL_SIZE * 0.4))

        if dev_show_coords:
            for gy in range(GRID_ROWS):
                for gx in range(GRID_COLS):
                    screen.blit(font_coords.render(f"{gx},{gy}", True, COLOR_DEV_COORDS), (gx*CELL_SIZE+2, gy*CELL_SIZE+2))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    print("\n" + "=" * 50 + "\n        GRID PUZZLE GAME\n" + "=" * 50)
    hint_input = input("Включить подсказки? ('да' или Enter): ").strip().lower()
    hints_enabled = hint_input in ("да", "yes", "y", "подсказывать")
    
    print("\nДоступные уровни:")
    for i, lvl in enumerate(LEVELS):
        print(f"  {i+1}. [{ 'SEQ' if lvl.get('type')=='sequence' else 'COND' }] {lvl.get('name', f'Уровень {i+1}')}")
    
    try:
        run_game(max(0, min(int(input(f"\nВыберите уровень (1-{len(LEVELS)}): ")) - 1, len(LEVELS) - 1)), hints_enabled)
    except: run_game(0, hints_enabled)
