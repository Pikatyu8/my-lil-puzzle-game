import pygame
import sys
import math
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
COLOR_POISON = (255, 50, 50)
COLOR_WALL = (128, 255, 176)
COLOR_REQUIREMENT = (100, 180, 255)
COLOR_REQUIREMENT_AVOID = (255, 100, 100)
COLOR_REQUIREMENT_END = (100, 255, 100)
COLOR_GLOBAL_REQ = (255, 220, 100)  # Жёлтый для глобальных условий

# Глобальные переменные
dev_recording = []
path_positions = []
game_running = True
dev_access_granted = False
dev_show_coords = False
dev_disable_victory = False  # <--- НОВАЯ ПЕРЕМЕННАЯ: Блокировка победы

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
            
            # --- ОБНОВЛЕННАЯ ЛОГИКА ДЛЯ СТЕН И ЯДА ---
            for key in ["poison", "walls"]:
                if key in lvl:
                    processed = []
                    for item in lvl[key]:
                        coords = tuple(item[0]) # Координаты всегда первые
                        
                        # 1. Поддержка старого формата: [[x,y], "side", "type"]
                        if len(item) == 3 and isinstance(item[1], str):
                            processed.append((coords, item[1], item[2]))
                        
                        # 2. Поддержка нового формата: [[x,y], {"down": "outer"}, {"right": "inner"}]
                        #    Или даже: [[x,y], {"down": "outer", "right": "inner"}]
                        else:
                            for part in item[1:]:
                                if isinstance(part, dict):
                                    for side, b_type in part.items():
                                        processed.append((coords, side, b_type))
                                        
                    lvl[key] = processed
            # -----------------------------------------
                        
        return data
    except Exception as e:
        print(f"[ERROR] Ошибка чтения JSON: {e}")
        sys.exit(1)

LEVELS = load_levels()

# =============================================================================
# ЛОГИКА ИГРЫ И ПРОВЕРКИ
# =============================================================================

def resolve_cells(cells_spec, grid_cols, grid_rows):
    if isinstance(cells_spec, list): 
        return [tuple(c) for c in cells_spec]
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

# =============================================================================
# СИСТЕМА ТРЕБОВАНИЙ
# =============================================================================

def get_condition_requirements(level_data, grid_cols, grid_rows):
    if level_data.get("type") != "condition":
        return {}, []
    
    requirements = {}
    global_reqs = []
    
    def add_req(cell, text, req_type="normal"):
        cell = tuple(cell)
        if cell not in requirements:
            requirements[cell] = []
        requirements[cell].append({"text": str(text), "type": req_type})
    
    def add_global_req(text, req_type="global"):
        global_reqs.append({"text": str(text), "type": req_type})
    
    def process_condition(cond):
        check_type = cond.get("check", "")
        
        if check_type == "group":
            for item in cond.get("items", []):
                process_condition(item)
            return
        
        cells = []
        if "cells" in cond:
            cells = resolve_cells(cond["cells"], grid_cols, grid_rows)
        
        if check_type == "cell_has_steps":
            required_steps = cond.get("required_steps", [])
            for cell in cells:
                for step in sorted(required_steps):
                    add_req(cell, step, "step")
        
        elif check_type == "visit_order":
            raw_cells = cond.get("cells", [])
            if isinstance(raw_cells, list):
                for i, cell in enumerate(raw_cells):
                    add_req(tuple(cell), str(i+1), "order")

        elif check_type == "first_visit_at_step":
            step = cond.get("step", 0)
            for cell in cells:
                add_req(cell, f"@{step}", "step")
        
        elif check_type == "last_visit_at_step":
            step = cond.get("step", 0)
            for cell in cells:
                add_req(cell, f"${step}", "step")
        
        elif check_type == "reach_before_step":
            step = cond.get("step", 0)
            for cell in cells:
                add_req(cell, f"<{step}", "step")
        
        elif check_type == "reach_after_step":
            step = cond.get("step", 0)
            for cell in cells:
                add_req(cell, f"≥{step}", "step")
        
        elif check_type == "visit_count":
            count = cond.get("count", 1)
            op = cond.get("operator", "==")
            op_symbols = {"==": "=", ">=": "≥", "<=": "≤", ">": ">", "<": "<"}
            symbol = op_symbols.get(op, op)
            for cell in cells:
                add_req(cell, f"x{symbol}{count}", "count")
        
        elif check_type == "consecutive_visits":
            count = cond.get("count", 2)
            for cell in cells:
                add_req(cell, f"⟳{count}", "count")
        
        elif check_type == "avoid_cells":
            for cell in cells:
                add_req(cell, "✕", "avoid")
        
        elif check_type == "end_at":
            for cell in cells:
                add_req(cell, "◎", "end")
        
        elif check_type == "visit_cells":
            for cell in cells:
                add_req(cell, "•", "visit")
        
        elif check_type == "no_revisit":
            exceptions = resolve_cells(cond.get("except", []), grid_cols, grid_rows)
            for cell in exceptions:
                add_req(cell, "∞", "special")
            if not exceptions:
                add_global_req("Без повторов", "global")
            else:
                add_global_req(f"Без повторов (кроме {len(exceptions)})", "global")
        
        elif check_type == "path_length_to_cell":
            count = cond.get("count", 0)
            op = cond.get("operator", "==")
            op_symbols = {"==": "=", ">=": "≥", "<=": "≤", ">": ">", "<": "<"}
            symbol = op_symbols.get(op, op)
            for cell in cells:
                add_req(cell, f"L{symbol}{count}", "step")
        
        elif check_type == "total_steps":
            count = cond.get("count", 0)
            op = cond.get("operator", "==")
            op_symbols = {"==": "=", ">=": "≥", "<=": "≤", ">": ">", "<": "<", "!=": "≠"}
            symbol = op_symbols.get(op, "=")
            add_global_req(f"Шагов: {symbol}{count}", "steps")
    
    for cond in level_data.get("conditions", []):
        process_condition(cond)
    
    return requirements, global_reqs

# =============================================================================
# РАСШИРЕННАЯ ЛОГИКА УСЛОВИЙ
# =============================================================================

def check_condition(condition, path_positions, player_pos, grid_cols, grid_rows):
    check_type = condition.get("check", "")
    
    if check_type == "group":
        logic = condition.get("logic", "AND").upper()
        items = condition.get("items", [])
        
        if logic == "AND":
            return all(check_condition(item, path_positions, player_pos, grid_cols, grid_rows) for item in items)
        elif logic == "OR":
            return any(check_condition(item, path_positions, player_pos, grid_cols, grid_rows) for item in items)
        elif logic == "NOT":
            if items:
                return not check_condition(items[0], path_positions, player_pos, grid_cols, grid_rows)
            return True
        elif logic == "XOR":
            true_count = sum(1 for item in items if check_condition(item, path_positions, player_pos, grid_cols, grid_rows))
            return true_count == 1
        elif logic == "NAND":
            return not all(check_condition(item, path_positions, player_pos, grid_cols, grid_rows) for item in items)
        elif logic == "NOR":
            return not any(check_condition(item, path_positions, player_pos, grid_cols, grid_rows) for item in items)
        return False

    # ... Остальные проверки условий (без изменений) ...
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
        ops = {"==": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b, "!=": lambda a, b: a != b}
        return ops.get(operator, lambda a, b: False)(actual, required)

    elif check_type == "end_at":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        return tuple(player_pos) in cells

    elif check_type == "avoid_cells":
        cells = set(resolve_cells(condition["cells"], grid_cols, grid_rows))
        visited = set(path_positions)
        return len(visited & cells) == 0

    elif check_type == "visit_count":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        required = condition.get("count", 1)
        operator = condition.get("operator", "==")
        match_mode = condition.get("match", "any")
        ops = {"==": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}
        op_func = ops.get(operator, lambda a, b: a == b)
        visit_counts = {}
        for pos in path_positions: visit_counts[pos] = visit_counts.get(pos, 0) + 1
        if match_mode == "any": return any(op_func(visit_counts.get(cell, 0), required) for cell in cells)
        else: return all(op_func(visit_counts.get(cell, 0), required) for cell in cells)

    elif check_type == "visit_order":
        cells = [tuple(c) for c in condition["cells"]]
        first_visit = {}
        for step, pos in enumerate(path_positions):
            if pos not in first_visit: first_visit[pos] = step
        prev_step = -1
        for cell in cells:
            if cell not in first_visit: return False
            if first_visit[cell] <= prev_step: return False
            prev_step = first_visit[cell]
        return True

    elif check_type == "reach_before_step":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        max_step = condition.get("step", 999)
        match_mode = condition.get("match", "any")
        first_visit = {}
        for step, pos in enumerate(path_positions):
            if pos not in first_visit: first_visit[pos] = step
        if match_mode == "any": return any(first_visit.get(cell, 9999) < max_step for cell in cells)
        else: return all(first_visit.get(cell, 9999) < max_step for cell in cells)

    elif check_type == "reach_after_step":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        min_step = condition.get("step", 0)
        match_mode = condition.get("match", "any")
        first_visit = {}
        for step, pos in enumerate(path_positions):
            if pos not in first_visit: first_visit[pos] = step
        if match_mode == "any": return any(first_visit.get(cell, 9999) >= min_step for cell in cells)
        else: return all(first_visit.get(cell, 9999) >= min_step for cell in cells)

    elif check_type == "first_visit_at_step":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        target_step = condition.get("step", 0)
        match_mode = condition.get("match", "any")
        first_visit = {}
        for step, pos in enumerate(path_positions):
            if pos not in first_visit: first_visit[pos] = step
        if match_mode == "any": return any(first_visit.get(cell, -1) == target_step for cell in cells)
        else: return all(first_visit.get(cell, -1) == target_step for cell in cells)

    elif check_type == "last_visit_at_step":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        target_step = condition.get("step", 0)
        match_mode = condition.get("match", "any")
        last_visit = {}
        for step, pos in enumerate(path_positions): last_visit[pos] = step
        if match_mode == "any": return any(last_visit.get(cell, -1) == target_step for cell in cells)
        else: return all(last_visit.get(cell, -1) == target_step for cell in cells)

    elif check_type == "path_length_to_cell":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        required = condition.get("count", 0)
        operator = condition.get("operator", "==")
        match_mode = condition.get("match", "any")
        ops = {"==": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}
        op_func = ops.get(operator, lambda a, b: a == b)
        first_visit = {}
        for step, pos in enumerate(path_positions):
            if pos not in first_visit: first_visit[pos] = step
        if match_mode == "any": return any(op_func(first_visit.get(cell, 9999), required) for cell in cells)
        else: return all(op_func(first_visit.get(cell, 9999), required) for cell in cells)

    elif check_type == "consecutive_visits":
        cells = resolve_cells(condition["cells"], grid_cols, grid_rows)
        required = condition.get("count", 2)
        match_mode = condition.get("match", "any")
        def max_consecutive(cell):
            max_count = 0; current = 0
            for pos in path_positions:
                if pos == cell: current += 1; max_count = max(max_count, current)
                else: current = 0
            return max_count
        if match_mode == "any": return any(max_consecutive(cell) >= required for cell in cells)
        else: return all(max_consecutive(cell) >= required for cell in cells)

    elif check_type == "no_revisit":
        exceptions = set(resolve_cells(condition.get("except", []), grid_cols, grid_rows))
        visit_counts = {}
        for pos in path_positions: visit_counts[pos] = visit_counts.get(pos, 0) + 1
        for pos, count in visit_counts.items():
            if count > 1 and pos not in exceptions: return False
        return True

    return False

def check_all_conditions(conditions, path_positions, player_pos, grid_cols, grid_rows):
    for cond in conditions:
        if not check_condition(cond, path_positions, player_pos, grid_cols, grid_rows):
            return False
    return True

def get_condition_cells(level_data, grid_cols, grid_rows):
    if level_data.get("type") != "condition": return []
    cells = set()
    def extract_cells(cond):
        if "cells" in cond: cells.update(resolve_cells(cond["cells"], grid_cols, grid_rows))
        if cond.get("check") == "group":
            for item in cond.get("items", []): extract_cells(item)
    for cond in level_data.get("conditions", []): extract_cells(cond)
    return list(cells)

# --- ЛОГИКА БАРЬЕРОВ ---

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
        if tuple(current_pos) == b_pos and b_side == move_dir:
            if b_type in ["inner", "both"]: return False
        if tuple(next_pos) == b_pos and b_side == entry_side:
            if b_type in ["outer", "both"]: return False
    return True

# =============================================================================
# ОТРИСОВКА
# =============================================================================

def draw_barriers(surface, barriers_data, color, cell_size):
    if not barriers_data: return
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

def draw_requirements(surface, requirements, cell_size, font):
    for pos, reqs in requirements.items():
        x, y = pos
        base_x = x * cell_size
        base_y = y * cell_size
        overlay = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (base_x, base_y))
        mini_size = cell_size // 3
        
        for i, req in enumerate(reqs[:9]):
            text = req["text"]
            req_type = req["type"]
            col = i % 3; row = i // 3
            center_x = base_x + col * mini_size + mini_size // 2
            center_y = base_y + row * mini_size + mini_size // 2
            radius = int(mini_size * 0.4)

            if req_type == "avoid":
                color = COLOR_REQUIREMENT_AVOID
                offset = int(radius * 0.8)
                pygame.draw.line(surface, color, (center_x - offset, center_y - offset), (center_x + offset, center_y + offset), 2)
                pygame.draw.line(surface, color, (center_x + offset, center_y - offset), (center_x - offset, center_y + offset), 2)
            elif req_type == "end":
                color = COLOR_REQUIREMENT_END
                pygame.draw.circle(surface, color, (center_x, center_y), radius, 1)
                pygame.draw.circle(surface, color, (center_x, center_y), radius // 2)
            elif req_type == "visit":
                color = (255, 255, 100)
                pygame.draw.circle(surface, color, (center_x, center_y), radius)
            elif req_type == "order":
                color = COLOR_REQUIREMENT
                pygame.draw.circle(surface, color, (center_x, center_y), radius, 1)
                ord_font = pygame.font.SysFont("Arial", int(mini_size * 0.6), bold=True)
                txt_surf = ord_font.render(text, True, color)
                txt_rect = txt_surf.get_rect(center=(center_x, center_y))
                surface.blit(txt_surf, txt_rect)
            elif "⟳" in text:
                count_val = text.replace("⟳", "")
                color = (255, 220, 100)
                req_font = font
                if len(count_val) > 1: req_font = pygame.font.SysFont("Arial", int(mini_size * 0.7), bold=True)
                txt_surf = req_font.render(count_val, True, color)
                txt_rect = txt_surf.get_rect(center=(center_x, center_y))
                surface.blit(txt_surf, txt_rect)
                arc_rect = pygame.Rect(center_x - radius, center_y - radius, radius * 2, radius * 2)
                pygame.draw.arc(surface, color, arc_rect, 0.5, 5.8, 2)
                tri_center = (center_x + radius, center_y)
                p1 = (tri_center[0] - 3, tri_center[1] - 4)
                p2 = (tri_center[0] + 3, tri_center[1] - 4)
                p3 = (tri_center[0], tri_center[1] + 3)
                pygame.draw.polygon(surface, color, [p1, p2, p3])
            else:
                if req_type in ("step", "order"): color = COLOR_REQUIREMENT
                else: color = (200, 200, 100)
                txt_surf = font.render(text, True, color)
                txt_rect = txt_surf.get_rect(center=(center_x, center_y))
                surface.blit(txt_surf, txt_rect)

def draw_global_requirements(surface, global_reqs, font, screen_width):
    if not global_reqs: return
    padding = 10
    y_offset = padding
    for req in global_reqs:
        text = req["text"]
        req_type = req["type"]
        color = COLOR_GLOBAL_REQ if req_type == "steps" else (200, 200, 200)
        txt_surf = font.render(text, True, color)
        txt_rect = txt_surf.get_rect()
        txt_rect.topright = (screen_width - padding, y_offset)
        bg_rect = txt_rect.inflate(10, 6)
        bg_rect.topright = (screen_width - padding + 5, y_offset - 3)
        pygame.draw.rect(surface, (20, 20, 20), bg_rect)
        pygame.draw.rect(surface, color, bg_rect, 1)
        surface.blit(txt_surf, txt_rect)
        y_offset += txt_rect.height + 10

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
    # Добавляем +1 к range, чтобы отрисовалась последняя линия справа и снизу
    for x in range(0, width + 1, cell_size): 
        pygame.draw.line(surface, COLOR_GRID, (x, 0), (x, height))
    for y in range(0, height + 1, cell_size): 
        pygame.draw.line(surface, COLOR_GRID, (0, y), (width, y))
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
                print(f"[INFO] Координаты: {'АКТИВНО' if dev_show_coords else 'НЕАКТИВНО'}\n")
                print_menu()
            elif cmd_clean == '4' or cmd_clean == 'cells':
                cell_map = {}
                for step, pos in enumerate(path_positions):
                    if pos not in cell_map: cell_map[pos] = []
                    cell_map[pos].append(step)
                print("\n=== ДАННЫЕ ПО КЛЕТКАМ ===")
                sorted_cells = sorted(cell_map.keys(), key=lambda k: (k[1], k[0]))
                for cell in sorted_cells: print(f"{cell[0]},{cell[1]}: {cell_map[cell]}")
                print("=========================\n")
            elif cmd_clean == '5':
                global dev_disable_victory
                dev_disable_victory = not dev_disable_victory
                print(f"[INFO] Отключение победы: {'АКТИВНО' if dev_disable_victory else 'НЕАКТИВНО'}\n")
                print_menu()
            elif cmd_clean == 'help': 
                print_menu()
            else: 
                print("Неизвестная команда.")
        except EOFError: break

def print_menu():
    c_stat = "АКТИВНО" if dev_show_coords else "НЕАКТИВНО"
    v_stat = "АКТИВНО" if dev_disable_victory else "НЕАКТИВНО"
    print(f"\n=== DEV МЕНЮ ===\n1. SHOW | 2. CLEAR | 3. COORDS - {c_stat} | 4. CELLS | 5. NO WIN - {v_stat} | help\n================")

# =============================================================================
# ОСНОВНОЙ ЦИКЛ
# =============================================================================

def run_game(selected_idx, hints_enabled):
    global game_running, dev_recording, dev_access_granted, path_positions, dev_disable_victory
    global WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS

    pygame.init()
    pygame.font.init()

    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    current_idx = selected_idx
    screen = None
    game_surface = None 
    GRID_OFFSET_X = 0
    GRID_OFFSET_Y = 0
    clock = pygame.time.Clock()

    player_pos = [0, 0]
    required_sequence = []
    player_history = []
    path_positions = []
    target_grid_pos = None
    level_type = "sequence"
    level_conditions = []
    condition_cells = []
    
    poison_data = [] 
    walls_data = []
    
    show_requirements = True
    level_requirements = {} 
    global_requirements = []

    console_thread = threading.Thread(target=console_listener, daemon=True)
    console_thread.start()

    def load_level_data(idx):
        nonlocal player_pos, required_sequence, player_history, target_grid_pos
        nonlocal level_type, level_conditions, condition_cells, poison_data, walls_data, screen, game_surface
        nonlocal GRID_OFFSET_X, GRID_OFFSET_Y, show_requirements, level_requirements, global_requirements
        global dev_recording, path_positions
        global WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS

        level_data = LEVELS[idx]
        GRID_COLS, GRID_ROWS = level_data.get("grid", (16, 12))
        
        # Расчет размеров сетки и окна
        max_w = screen_w * 0.85 
        max_h = screen_h * 0.85
        CELL_SIZE = int(min(max_w // GRID_COLS, max_h // GRID_ROWS))
        
        grid_pix_w = CELL_SIZE * GRID_COLS
        grid_pix_h = CELL_SIZE * GRID_ROWS
        
        # Отступ 5%
        GRID_OFFSET_X = int(grid_pix_w * 0.05)
        GRID_OFFSET_Y = int(grid_pix_h * 0.05)
        
        WINDOW_WIDTH = grid_pix_w + GRID_OFFSET_X * 2
        WINDOW_HEIGHT = grid_pix_h + GRID_OFFSET_Y * 2
        
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        # Surface для игрового поля
        game_surface = pygame.Surface((grid_pix_w + 1, grid_pix_h + 1), pygame.SRCALPHA)
        
        level_type = level_data.get("type", "sequence")
        start = level_data["start"]
        player_pos = list(start)
        player_history = []
        dev_recording.clear()
        path_positions = [tuple(player_pos)]
        
        poison_data = level_data.get("poison", [])[:]
        walls_data = level_data.get("walls", [])[:]

        # Обработка wall_is_poison
        wall_poison_flag = level_data.get("wall_is_poison", False)
        if wall_poison_flag:
            exceptions = []
            if isinstance(wall_poison_flag, dict):
                exceptions = [tuple(c) for c in wall_poison_flag.get("except", [])]
            
            new_walls = []
            for w in walls_data:
                if w[0] not in exceptions:
                    poison_data.append(w)
                else:
                    new_walls.append(w)
            walls_data = new_walls

        show_requirements = True
        level_requirements, global_requirements = get_condition_requirements(level_data, GRID_COLS, GRID_ROWS)
        
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
        if walls_data: print(f"Стены (зелёные): {len(walls_data)}")
        if poison_data: print(f"Яд (красные): {len(poison_data)}")
        if level_requirements or global_requirements: 
            print(f"[X] - показать/скрыть требования")
        print(f"{'='*50}\n")

    load_level_data(current_idx)
    
    font_steps = pygame.font.SysFont("Arial", max(10, CELL_SIZE // 4))
    font_steps_small = pygame.font.SysFont("Arial", max(8, CELL_SIZE // 5))
    font_coords = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 3), bold=True)
    font_requirements = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 4), bold=True)
    # Уменьшенный шрифт глобальных условий
    font_global = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 4), bold=True)

    while game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: game_running = False
            
            if event.type == pygame.KEYDOWN:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_F9] and keys[pygame.K_F11]:
                    dev_access_granted = True; print_menu()

                if event.key == pygame.K_r:
                    load_level_data(current_idx)
                    # Сброс шрифтов при рестарте (на случай изменения размера окна/ячеек)
                    font_steps = pygame.font.SysFont("Arial", max(10, CELL_SIZE // 4))
                    font_steps_small = pygame.font.SysFont("Arial", max(8, CELL_SIZE // 5))
                    font_coords = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 3), bold=True)
                    font_requirements = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 4), bold=True)
                    font_global = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 4), bold=True)
                    continue
                
                if event.key == pygame.K_x:
                    show_requirements = not show_requirements
                    status = "ВКЛ" if show_requirements else "ВЫКЛ"
                    print(f"[INFO] Отображение требований: {status}")
                    continue

                move_attempt = None
                dx, dy = 0, 0
                
                if event.key == pygame.K_UP:    dx, dy = 0, -1; move_attempt = "u"
                elif event.key == pygame.K_DOWN:  dx, dy = 0, 1;  move_attempt = "d"
                elif event.key == pygame.K_LEFT:  dx, dy = -1, 0; move_attempt = "l"
                elif event.key == pygame.K_RIGHT: dx, dy = 1, 0;  move_attempt = "r"

                if move_attempt:
                    if show_requirements and len(path_positions) == 1:
                        show_requirements = False
                    
                    target_pos = [player_pos[0] + dx, player_pos[1] + dy]
                    in_bounds = (0 <= target_pos[0] < GRID_COLS and 0 <= target_pos[1] < GRID_ROWS)
                    
                    hit_poison = not is_path_clear(player_pos, target_pos, poison_data)
                    blocked_by_wall = not is_path_clear(player_pos, target_pos, walls_data)

                    if hit_poison:
                        print("☠ ВЫ ПОГИБЛИ! (Задели ядовитый барьер)")
                        load_level_data(current_idx)
                        continue

                    if not in_bounds or blocked_by_wall: pass
                    else: player_pos = target_pos

                    player_history.append(move_attempt)
                    dev_recording.append(move_attempt)
                    path_positions.append(tuple(player_pos))

                    level_complete = False
                    if level_type == "sequence":
                        if player_history == required_sequence: level_complete = True
                        elif len(player_history) >= len(required_sequence):
                             if hints_enabled: print("Неверная последовательность! Жмите 'R'.")
                    else:
                        if check_all_conditions(level_conditions, path_positions, player_pos, GRID_COLS, GRID_ROWS):
                            level_complete = True
                    
                    if level_complete:
                        if dev_disable_victory:
                            print(f"[DEV] Условие победы выполнено, но переход отключен.")
                        else:
                            print(f"✓ Уровень {current_idx + 1} ПРОЙДЕН!")
                            current_idx += 1
                            if current_idx < len(LEVELS):
                                load_level_data(current_idx)
                                font_steps = pygame.font.SysFont("Arial", max(10, CELL_SIZE // 4))
                                font_steps_small = pygame.font.SysFont("Arial", max(8, CELL_SIZE // 5))
                                font_coords = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 3), bold=True)
                                font_requirements = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 4), bold=True)
                                font_global = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 4), bold=True)
                            else:
                                print("\n🎉 ВЫ ПРОШЛИ ВСЮ ИГРУ! 🎉")
                                game_running = False

        # --- ОТРИСОВКА ---
        screen.fill(COLOR_BG)
        game_surface.fill(COLOR_BG)
        
        # 1. СЕТКА И ЗОНЫ
        draw_grid(game_surface, GRID_COLS*CELL_SIZE, GRID_ROWS*CELL_SIZE, CELL_SIZE)
        
        if level_type == "sequence" and target_grid_pos:
            pygame.draw.rect(game_surface, COLOR_TARGET, (target_grid_pos[0]*CELL_SIZE, target_grid_pos[1]*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        
        if level_type == "condition":
            for cell in condition_cells:
                pygame.draw.rect(game_surface, COLOR_CONDITION_HINT, (cell[0]*CELL_SIZE, cell[1]*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        
        # 2. БАРЬЕРЫ
        draw_barriers(game_surface, walls_data, COLOR_WALL, CELL_SIZE)
        draw_barriers(game_surface, poison_data, COLOR_POISON, CELL_SIZE)

        # 3. ШАГИ (под игроком)
        # Если включен режим требований, шаги не рисуем, чтобы не перегружать
        if not (show_requirements and (level_requirements or global_requirements)):
            cell_data = {}
            for step_num, pos in enumerate(path_positions):
                if pos not in cell_data: cell_data[pos] = []
                if len(cell_data[pos]) < 9: cell_data[pos].append(step_num)
            for pos, steps in cell_data.items():
                for i, val in enumerate(steps):
                    current_font = font_steps_small if val >= 100 else font_steps
                    txt_surf = current_font.render(str(val), True, COLOR_TEXT)
                    game_surface.blit(txt_surf, (pos[0]*CELL_SIZE+2+(i%3)*(CELL_SIZE//3), pos[1]*CELL_SIZE+2+(i//3)*(CELL_SIZE//3)))

        # 4. ИГРОК
        px, py = player_pos[0]*CELL_SIZE + CELL_SIZE//2, player_pos[1]*CELL_SIZE + CELL_SIZE//2
        pygame.draw.circle(game_surface, COLOR_PLAYER, (px, py), int(CELL_SIZE * 0.4))

        # 5. ЛОКАЛЬНЫЕ ТРЕБОВАНИЯ (поверх игрока)
        if show_requirements and level_requirements:
            draw_requirements(game_surface, level_requirements, CELL_SIZE, font_requirements)

        # 6. DEV КООРДИНАТЫ (правый нижний угол клетки)
        if dev_show_coords:
            for gy in range(GRID_ROWS):
                for gx in range(GRID_COLS):
                    coord_text = f"{gx},{gy}"
                    txt_surf = font_coords.render(coord_text, True, COLOR_DEV_COORDS)
                    tx = (gx + 1) * CELL_SIZE - txt_surf.get_width() - 3
                    ty = (gy + 1) * CELL_SIZE - txt_surf.get_height() - 3
                    game_surface.blit(txt_surf, (tx, ty))

        # 7. НАКЛАДЫВАЕМ ПОЛЕ НА ЭКРАН
        screen.blit(game_surface, (GRID_OFFSET_X, GRID_OFFSET_Y))

        # 8. ГЛОБАЛЬНЫЕ ТРЕБОВАНИЯ (Поверх всего экрана)
        if show_requirements and global_requirements:
            draw_global_requirements(screen, global_requirements, font_global, WINDOW_WIDTH)

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
