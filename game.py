import pygame
import sys
import threading
import json
import os
# из проекта
import savestates
import editor

# --- ЦВЕТА ---
COLOR_BG = (0, 0, 0)
COLOR_GRID = (255, 255, 255)
COLOR_PLAYER = (255, 255, 255)
COLOR_TARGET = (64, 64, 64)
COLOR_TEXT = (150, 150, 150)
COLOR_DEV_COORDS = (255, 165, 0)
COLOR_CONDITION_HINT = (40, 60, 40)

COLOR_POISON = (255, 50, 50)
COLOR_WALL = (128, 255, 176)
COLOR_REQUIREMENT = (100, 180, 255)
COLOR_REQUIREMENT_AVOID = (255, 100, 100)
COLOR_REQUIREMENT_END = (100, 255, 100)
COLOR_GLOBAL_REQ = (255, 220, 100)
COLOR_AVOID_STEP = (255, 80, 180)
COLOR_REQUIRE_STEP = (100, 255, 150)
COLOR_EDITOR_MODE = (255, 100, 255)

# Глобальные переменные
dev_recording = []
path_positions = []
game_running = True
dev_access_granted = False
dev_show_coords = False
dev_disable_victory = False
editor_mode = False

SIDE_PANEL_WIDTH = 250 
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 50
GRID_COLS = 16
GRID_ROWS = 12
LEVELS = []

# =============================================================================
# РАБОТА С ФАЙЛАМИ
# =============================================================================

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# =============================================================================
# НОВАЯ СИСТЕМА ПАРСИНГА БАРЬЕРОВ
# =============================================================================

class BarrierParser:
    """Парсер барьеров с поддержкой нового консистентного формата."""
    
    SIDE_MAP = {
        'u': 'up', 'd': 'down', 'l': 'left', 'r': 'right',
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'
    }
    ALL_SIDES = ['up', 'down', 'left', 'right']
    
    @classmethod
    def parse_sides(cls, sides_str):
        """
        Парсит строку сторон.
        "all" / "lrud" → все стороны
        "ud" → up, down
        "l" → left
        """
        if not sides_str or sides_str in ["all", "box", "square", "lrud", "udlr"]:
            return cls.ALL_SIDES[:]
        
        result = []
        for c in sides_str.lower():
            if c in cls.SIDE_MAP:
                side = cls.SIDE_MAP[c]
                if side not in result:
                    result.append(side)
        return result if result else cls.ALL_SIDES[:]
    
    @classmethod
    def generate_rect_cells(cls, start, end):
        """Генерирует все клетки в прямоугольнике."""
        x1, y1 = int(start[0]), int(start[1])
        x2, y2 = int(end[0]), int(end[1])
        return [
            (x, y)
            for x in range(min(x1, x2), max(x1, x2) + 1)
            for y in range(min(y1, y2), max(y1, y2) + 1)
        ]
    
    @classmethod
    def generate_perimeter(cls, start, end, sides):
        """Генерирует стены по периметру прямоугольника."""
        x1 = min(int(start[0]), int(end[0]))
        y1 = min(int(start[1]), int(end[1]))
        x2 = max(int(start[0]), int(end[0]))
        y2 = max(int(start[1]), int(end[1]))
        
        result = []
        if 'left' in sides:
            result.extend(((x1, y), 'left') for y in range(y1, y2 + 1))
        if 'right' in sides:
            result.extend(((x2, y), 'right') for y in range(y1, y2 + 1))
        if 'up' in sides:
            result.extend(((x, y1), 'up') for x in range(x1, x2 + 1))
        if 'down' in sides:
            result.extend(((x, y2), 'down') for x in range(x1, x2 + 1))
        return result
    
    @classmethod
    def is_new_format(cls, item):
        """Проверяет, использует ли элемент новый формат."""
        return isinstance(item, dict) and any(
            key in item for key in ["cell", "cells", "range", "ranges", "type", "sides", "mode"]
        )
    
    @classmethod
    def is_coord(cls, item):
        """Проверяет, является ли item координатой [x, y]."""
        return (isinstance(item, list) and len(item) == 2 and
                isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)))
    
    @classmethod
    def parse_item(cls, item, default_type="both"):
        """
        Парсит один элемент барьера.
        
        НОВЫЙ ФОРМАТ (рекомендуется):
        {
            "cell": [x, y],           # одна ячейка
            "cells": [[x,y], ...],    # несколько ячеек
            "range": [[x1,y1], [x2,y2]],    # диапазон
            "ranges": [[[x1,y1],[x2,y2]], ...],  # несколько диапазонов
            "sides": "all" / "ud" / "lr" / "lrud" / "u" / "d" / "l" / "r",
            "mode": "fill" / "perimeter",   # fill по умолчанию
            "type": "both" / "inner" / "outer",
            "except": [...]   # исключения (тот же формат)
        }
        
        Возвращает: список кортежей (cell, side, barrier_type)
        """
        if not isinstance(item, dict):
            return []
        
        walls = []
        b_type = item.get("type", default_type)
        mode = item.get("mode", "fill")
        sides_str = item.get("sides", "all")
        sides = cls.parse_sides(sides_str)
        
        # Собираем все targets
        targets = []
        
        # Одиночная ячейка
        if "cell" in item:
            c = item["cell"]
            targets.append(("cell", (int(c[0]), int(c[1]))))
        
        # Массив ячеек
        if "cells" in item:
            for c in item["cells"]:
                targets.append(("cell", (int(c[0]), int(c[1]))))
        
        # Один диапазон
        if "range" in item:
            r = item["range"]
            targets.append(("range", 
                           (int(r[0][0]), int(r[0][1])),
                           (int(r[1][0]), int(r[1][1]))))
        
        # Несколько диапазонов
        if "ranges" in item:
            for r in item["ranges"]:
                targets.append(("range",
                               (int(r[0][0]), int(r[0][1])),
                               (int(r[1][0]), int(r[1][1]))))
        
        # Обрабатываем исключения
        except_set = set()
        if "except" in item:
            for exc in item["except"]:
                if isinstance(exc, dict):
                    for coords, side, _ in cls.parse_item(exc, b_type):
                        except_set.add((coords, side))
        
        # Генерируем стены
        for target in targets:
            if target[0] == "cell":
                cell = target[1]
                for side in sides:
                    if (cell, side) not in except_set:
                        walls.append((cell, side, b_type))
            
            elif target[0] == "range":
                start, end = target[1], target[2]
                
                if mode == "perimeter":
                    for coords, side in cls.generate_perimeter(start, end, sides):
                        if (coords, side) not in except_set:
                            walls.append((coords, side, b_type))
                else:  # fill
                    for cell in cls.generate_rect_cells(start, end):
                        for side in sides:
                            if (cell, side) not in except_set:
                                walls.append((cell, side, b_type))
        
        return walls
    
    @classmethod
    def parse_legacy_item(cls, item):
        """
        Парсит элемент в СТАРОМ формате для обратной совместимости.
        Старый формат: [[coords], {sides_dict}]
        
        Поддержка сторон периметра в modes:
        {"": "both", "modes": ["perimeter", "ldr"]} → периметр только по left, down, right
        """
        if not isinstance(item, list) or len(item) != 2:
            return []
        
        raw_target, sides_dict = item[0], item[1]
        if not isinstance(sides_dict, dict):
            return []
        
        walls = []
        modes = sides_dict.get("modes", [])
        except_spec = sides_dict.get("except", [])
        
        # Определяем режим
        is_perimeter = "perimeter" in modes or "box" in modes
        
        # ИСПРАВЛЕНИЕ: ищем стороны периметра в modes
        perimeter_sides_override = None
        if is_perimeter:
            for m in modes:
                if m not in ["perimeter", "box", "fill", "standart", "standard"]:
                    # Проверяем, похоже ли на строку сторон (только l, r, u, d)
                    if m and all(c.lower() in "lrud" for c in m):
                        perimeter_sides_override = cls.parse_sides(m)
                        break
        
        # Парсим исключения (рекурсивно)
        except_set = set()
        for exc in except_spec:
            if cls.is_new_format(exc):
                for coords, side, _ in cls.parse_item(exc):
                    except_set.add((coords, side))
            elif isinstance(exc, list):
                if cls.is_coord(exc):
                    cell = (int(exc[0]), int(exc[1]))
                    for side in cls.ALL_SIDES:
                        except_set.add((cell, side))
                elif len(exc) == 2 and cls.is_coord(exc[0]) and cls.is_coord(exc[1]):
                    for cell in cls.generate_rect_cells(exc[0], exc[1]):
                        for side in cls.ALL_SIDES:
                            except_set.add((cell, side))
        
        # Определяем targets
        def is_range(r):
            return (isinstance(r, list) and len(r) == 2 and
                    cls.is_coord(r[0]) and cls.is_coord(r[1]))
        
        def is_multi_range(r):
            return isinstance(r, list) and all(is_range(x) for x in r)
        
        ranges = []
        if is_multi_range(raw_target):
            for r in raw_target:
                ranges.append((tuple(r[0]), tuple(r[1])))
        elif is_range(raw_target):
            ranges.append((tuple(raw_target[0]), tuple(raw_target[1])))
        else:
            if cls.is_coord(raw_target):
                ranges.append((tuple(raw_target), tuple(raw_target)))
            elif isinstance(raw_target, list):
                for c in raw_target:
                    if cls.is_coord(c):
                        ranges.append((tuple(c), tuple(c)))
        
        # Обрабатываем стороны
        for sides_key, b_type in sides_dict.items():
            if sides_key in ["modes", "except"]:
                continue
            if b_type not in ["inner", "outer", "both"]:
                continue
            
            # Определяем стороны из ключа
            sides = cls.parse_sides(sides_key) if sides_key else cls.ALL_SIDES
            
            # ИСПРАВЛЕНИЕ: для периметра используем стороны из modes, если указаны
            if is_perimeter and perimeter_sides_override is not None:
                sides = perimeter_sides_override
            
            for start, end in ranges:
                if is_perimeter:
                    for coords, side in cls.generate_perimeter(start, end, sides):
                        if (coords, side) not in except_set:
                            walls.append((coords, side, b_type))
                else:
                    for cell in cls.generate_rect_cells(start, end):
                        for side in sides:
                            if (cell, side) not in except_set:
                                walls.append((cell, side, b_type))
        
        return walls


def process_level_data(data):
    """Обрабатывает данные уровней с поддержкой нового и старого форматов."""
    
    for lvl in data:
        # Конвертируем базовые поля
        if "grid" in lvl:
            lvl["grid"] = tuple(lvl["grid"])
        if "start" in lvl:
            lvl["start"] = tuple(lvl["start"])
        
        # Обработка conditions
        if "conditions" in lvl:
            cols, rows = lvl.get("grid", (16, 12))
            for cond in lvl["conditions"]:
                if "cells" in cond:
                    c = cond["cells"]
                    if isinstance(c, list) and len(c) > 0:
                        if isinstance(c[0], (int, float)):
                            cond["cells"] = [tuple(c)]
                        else:
                            cond["cells"] = [tuple(item) for item in c]
        
        # Обработка poison и walls
        for key in ["poison", "walls"]:
            if key not in lvl:
                continue
            
            processed = []
            for item in lvl[key]:
                if BarrierParser.is_new_format(item):
                    # НОВЫЙ формат
                    processed.extend(BarrierParser.parse_item(item))
                else:
                    # СТАРЫЙ формат (обратная совместимость)
                    processed.extend(BarrierParser.parse_legacy_item(item))
            
            lvl[key] = processed
    
    return data


def load_levels_from_file(filename, is_internal=True):
    if is_internal:
        path = resource_path(filename)
    else:
        path = os.path.abspath(filename)

    if not os.path.exists(path):
        print(f"[ERROR] Файл не найден: {path}")
        return None

    try:
        print(f"[LOAD] {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return process_level_data(data)
    except Exception as e:
        print(f"[ERROR] JSON: {e}")
        import traceback
        traceback.print_exc()
        return None

# =============================================================================
# РАБОТА СО ШРИФТАМИ
# =============================================================================
_font_cache = {}

def get_font(size, bold=False):
    """Возвращает кэшированный шрифт с поддержкой Unicode."""
    key = (size, bold)
    if key not in _font_cache:
        font_names = ["Arial", "Segoe UI", "Tahoma", "DejaVu Sans", "Liberation Sans"]
        font = None
        for name in font_names:
            try:
                font = pygame.font.SysFont(name, size, bold=bold)
                if font.get_height() > 0:
                    break
            except:
                continue
        if font is None:
            font = pygame.font.Font(None, size)
        _font_cache[key] = font
    return _font_cache[key]

# =============================================================================
# УТИЛИТЫ
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

def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0: return False
    return True

def eval_step_expr(expr, step):
    expr = expr.strip()
    if "|" in expr:
        return any(eval_step_expr(p.strip(), step) for p in expr.split("|"))
    if "&" in expr:
        return all(eval_step_expr(p.strip(), step) for p in expr.split("&"))
    if expr.startswith("!"):
        return not eval_step_expr(expr[1:], step)
    
    if expr == "even": return step % 2 == 0
    elif expr == "odd": return step % 2 == 1
    elif expr == "prime": return is_prime(step)
    elif expr.startswith("div:"): return step % int(expr.split(":")[1]) == 0
    elif expr.startswith("mod:"):
        parts = expr.split(":")
        return step % int(parts[1]) == int(parts[2])
    elif expr.startswith("range:"):
        parts = expr.split(":")
        return int(parts[1]) <= step <= int(parts[2])
    elif expr.startswith("gt:"): return step > int(expr.split(":")[1])
    elif expr.startswith("lt:"): return step < int(expr.split(":")[1])
    elif expr.startswith("gte:"): return step >= int(expr.split(":")[1])
    elif expr.startswith("lte:"): return step <= int(expr.split(":")[1])
    return False

def parse_steps(condition, max_steps=500):
    result = set()
    if "step_expr" in condition:
        for s in range(max_steps):
            if eval_step_expr(condition["step_expr"], s):
                result.add(s)
        return result
    if "step" in condition: result.add(condition["step"])
    if "steps" in condition: result.update(condition["steps"])
    if "step_range" in condition:
        start, end = condition["step_range"]
        result.update(range(start, end + 1))
    return result

def format_steps(condition):
    if "step_expr" in condition:
        expr = condition["step_expr"]
        for old, new in [("even", "2n"), ("odd", "2n+1"), ("prime", "P")]:
            expr = expr.replace(old, new)
        return expr.replace("div:", "÷").replace("range:", "")
    
    parts = []
    if "step" in condition: parts.append(str(condition["step"]))
    if "steps" in condition:
        steps = condition["steps"]
        parts.append(",".join(map(str, steps)) if len(steps) <= 3 else f"{min(steps)}..{max(steps)}")
    if "step_range" in condition:
        s, e = condition["step_range"]
        parts.append(f"{s}-{e}")
    return ",".join(parts) if parts else "?"

OPERATORS = {
    "==": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b, "<": lambda a, b: a < b, "!=": lambda a, b: a != b,
    "=": lambda a, b: a == b,
}
OP_SYMBOLS = {"==": "=", ">=": "≥", "<=": "≤", ">": ">", "<": "<", "!=": "≠"}

# =============================================================================
# ПРОВЕРКА УСЛОВИЙ
# =============================================================================

def check_condition(cond, path, player_pos, cols, rows):
    check = cond.get("check", "")
    cells = resolve_cells(cond.get("cells", []), cols, rows)
    match = cond.get("match", "all")
    
    if check == "group":
        logic = cond.get("logic", "AND").upper()
        items = cond.get("items", [])
        results = [check_condition(item, path, player_pos, cols, rows) for item in items]
        if logic == "AND": return all(results)
        elif logic == "OR": return any(results)
        elif logic == "NOT": return not results[0] if results else True
        elif logic == "XOR": return sum(results) == 1
        return False
    
    if check == "visit":
        visit_counts = {}
        for pos in path:
            visit_counts[pos] = visit_counts.get(pos, 0) + 1
        
        if "min" in cond or "max" in cond:
            min_c, max_c = cond.get("min", 0), cond.get("max", 999999)
            if match == "any":
                return any(min_c <= visit_counts.get(c, 0) <= max_c for c in cells)
            return all(min_c <= visit_counts.get(c, 0) <= max_c for c in cells)
        
        count = cond.get("count", 1)
        op_func = OPERATORS.get(cond.get("operator", ">="), OPERATORS[">="])
        if match == "any":
            return any(op_func(visit_counts.get(c, 0), count) for c in cells)
        return all(op_func(visit_counts.get(c, 0), count) for c in cells)
    
    if check == "at_steps":
        mode = cond.get("mode", "require")
        cells_set = set(cells)
        
        if "step_expr" in cond:
            expr = cond["step_expr"]
            if mode == "avoid":
                for i, pos in enumerate(path):
                    if pos in cells_set and eval_step_expr(expr, i):
                        return False
                return True
            else:
                cell_valid = {c: False for c in cells}
                for i, pos in enumerate(path):
                    if pos in cells_set and eval_step_expr(expr, i):
                        cell_valid[pos] = True
                return any(cell_valid.values()) if match == "any" else all(cell_valid.get(c, False) for c in cells)
        
        target_steps = parse_steps(cond)
        cell_steps = {}
        for i, pos in enumerate(path):
            if pos not in cell_steps: cell_steps[pos] = set()
            cell_steps[pos].add(i)
        
        if mode == "avoid":
            for i, pos in enumerate(path):
                if pos in cells_set and i in target_steps:
                    return False
            return True
        else:
            if match == "any":
                return any(c in cell_steps and target_steps.issubset(cell_steps[c]) for c in cells)
            return all(c in cell_steps and target_steps.issubset(cell_steps[c]) for c in cells)
    
    if check == "end_at":
        return tuple(player_pos) in cells
    
    if check == "order":
        first_visits = {}
        for i, pos in enumerate(path):
            if pos not in first_visits: first_visits[pos] = i
        prev = -1
        for c in cells:
            if c not in first_visits or first_visits[c] <= prev:
                return False
            prev = first_visits[c]
        return True
    
    if check == "consecutive":
        count = cond.get("count", 2)
        def max_consecutive(cell):
            max_c = current = 0
            for pos in path:
                if pos == cell:
                    current += 1
                    max_c = max(max_c, current)
                else:
                    current = 0
            return max_c
        if match == "any":
            return any(max_consecutive(c) >= count for c in cells)
        return all(max_consecutive(c) >= count for c in cells)
    
    if check == "no_revisit":
        exceptions = set(resolve_cells(cond.get("except", []), cols, rows))
        visit_counts = {}
        for pos in path:
            visit_counts[pos] = visit_counts.get(pos, 0) + 1
        for pos, cnt in visit_counts.items():
            if cnt > 1 and pos not in exceptions:
                return False
        return True
    
    if check == "total_steps":
        count = cond.get("count", 0)
        op_func = OPERATORS.get(cond.get("operator", "=="), OPERATORS["=="])
        return op_func(len(path) - 1, count)
    
    return False

def check_all_conditions(conditions, path, player_pos, cols, rows):
    return all(check_condition(c, path, player_pos, cols, rows) for c in conditions)

def get_condition_cells(level_data, cols, rows):
    if level_data.get("type") != "condition":
        return []
    cells = set()
    def extract(cond):
        if "cells" in cond:
            cells.update(resolve_cells(cond["cells"], cols, rows))
        if cond.get("check") == "group":
            for item in cond.get("items", []):
                extract(item)
    for cond in level_data.get("conditions", []):
        extract(cond)
    return list(cells)

# =============================================================================
# СИСТЕМА ТРЕБОВАНИЙ
# =============================================================================

def get_condition_requirements(level_data, cols, rows):
    if level_data.get("type") != "condition":
        return {}, []
    
    requirements = {}
    global_reqs = []
    
    def add_req(cell, text, req_type="normal"):
        cell = tuple(cell)
        if cell not in requirements: requirements[cell] = []
        requirements[cell].append({"text": str(text), "type": req_type})
    
    def add_global(text, req_type="global"):
        global_reqs.append({"text": str(text), "type": req_type})
    
    def process(cond):
        check = cond.get("check", "")
        cells = resolve_cells(cond.get("cells", []), cols, rows)
        
        if check == "group":
            for item in cond.get("items", []): process(item)
            return
        
        if check == "visit":
            if "min" in cond or "max" in cond:
                min_c, max_c = cond.get("min", 0), cond.get("max", 999999)
                text = f"≥{min_c}" if max_c >= 999999 else f"≤{max_c}" if min_c <= 0 else f"{min_c}-{max_c}"
                for c in cells: add_req(c, f"×{text}", "count")
            else:
                count = cond.get("count", 1)
                op = cond.get("operator", ">=")
                if count == 0:
                    for c in cells: add_req(c, "✕", "avoid")
                elif count == 1 and op in (">=", "==", "="):
                    for c in cells: add_req(c, "•", "visit")
                else:
                    for c in cells: add_req(c, f"×{OP_SYMBOLS.get(op, op)}{count}", "count")
        
        elif check == "at_steps":
            step_text = format_steps(cond)
            mode = cond.get("mode", "require")
            for c in cells:
                add_req(c, f"⊘{step_text}" if mode == "avoid" else f"✓{step_text}", 
                       "avoid_step" if mode == "avoid" else "require_step")
        
        elif check == "end_at":
            for c in cells: add_req(c, "◎", "end")
        
        elif check == "order":
            for i, c in enumerate(cells): add_req(c, str(i + 1), "order")
        
        elif check == "consecutive":
            for c in cells: add_req(c, f"⟳{cond.get('count', 2)}", "consecutive")
        
        elif check == "no_revisit":
            exceptions = resolve_cells(cond.get("except", []), cols, rows)
            for c in exceptions: add_req(c, "∞", "special")
            add_global(f"Без повторов{f' (кроме {len(exceptions)})' if exceptions else ''}", "global")
        
        elif check == "total_steps":
            count = cond.get("count", 0)
            add_global(f"Шагов: {OP_SYMBOLS.get(cond.get('operator', '=='), '=')}{count}", "steps")
    
    for cond in level_data.get("conditions", []):
        process(cond)
    
    return requirements, global_reqs

# =============================================================================
# БАРЬЕРЫ
# =============================================================================

def is_path_clear(current_pos, next_pos, barriers_data):
    if not barriers_data:
        return True

    cx, cy = current_pos
    nx, ny = next_pos
    
    if nx > cx: move_dir = "right"
    elif nx < cx: move_dir = "left"
    elif ny > cy: move_dir = "down"
    elif ny < cy: move_dir = "up"
    else: return True
    
    opposite = {"right": "left", "left": "right", "down": "up", "up": "down"}
    entry_side = opposite[move_dir]

    for b_pos, b_side, b_type in barriers_data:
        if tuple(current_pos) == b_pos and b_side == move_dir and b_type in ["inner", "both"]:
            return False
        if tuple(next_pos) == b_pos and b_side == entry_side and b_type in ["outer", "both"]:
            return False
    return True

# =============================================================================
# ОТРИСОВКА
# =============================================================================

def draw_grid(surface, width, height, cell_size):
    for x in range(0, width + 1, cell_size):
        pygame.draw.line(surface, COLOR_GRID, (x, 0), (x, height))
    for y in range(0, height + 1, cell_size):
        pygame.draw.line(surface, COLOR_GRID, (0, y), (width, y))

def draw_barriers(surface, barriers_data, color, cell_size):
    if not barriers_data:
        return
    for b_pos, side, b_type in barriers_data:
        px, py = b_pos
        x, y = px * cell_size, py * cell_size
        
        if side == "up": start, end = (x, y), (x + cell_size, y)
        elif side == "down": start, end = (x, y + cell_size), (x + cell_size, y + cell_size)
        elif side == "left": start, end = (x, y), (x, y + cell_size)
        elif side == "right": start, end = (x + cell_size, y), (x + cell_size, y + cell_size)
        else: continue
        
        pygame.draw.line(surface, color, start, end, 5 if b_type == "both" else 3)
        
        if b_type != "both":
            mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            offset = 6
            if side == "up":
                dy = -offset if b_type == "outer" else offset
                pts = [(mid_x, mid_y + dy), (mid_x - 4, mid_y), (mid_x + 4, mid_y)]
            elif side == "down":
                dy = offset if b_type == "outer" else -offset
                pts = [(mid_x, mid_y + dy), (mid_x - 4, mid_y), (mid_x + 4, mid_y)]
            elif side == "left":
                dx = -offset if b_type == "outer" else offset
                pts = [(mid_x + dx, mid_y), (mid_x, mid_y - 4), (mid_x, mid_y + 4)]
            elif side == "right":
                dx = offset if b_type == "outer" else -offset
                pts = [(mid_x + dx, mid_y), (mid_x, mid_y - 4), (mid_x, mid_y + 4)]
            pygame.draw.polygon(surface, color, pts)

def draw_requirements(surface, requirements, cell_size):
    mini = cell_size // 3
    font_size_base = int(mini * 0.65)
    
    for pos, reqs in requirements.items():
        x, y = pos
        base_x, base_y = x * cell_size, y * cell_size
        
        overlay = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (base_x, base_y))
        
        for i, req in enumerate(reqs[:9]):
            text, req_type = req["text"], req["type"]
            col, row = i % 3, i // 3
            cx = base_x + col * mini + mini // 2
            cy = base_y + row * mini + mini // 2
            r = int(mini * 0.4)
            
            colors = {
                "avoid": COLOR_REQUIREMENT_AVOID, "avoid_step": COLOR_AVOID_STEP,
                "require_step": COLOR_REQUIRE_STEP, "end": COLOR_REQUIREMENT_END,
                "visit": (255, 255, 100), "consecutive": (255, 220, 100),
                "step": COLOR_REQUIREMENT, "order": COLOR_REQUIREMENT
            }
            color = colors.get(req_type, (200, 200, 100))
            
            if req_type == "avoid":
                off = int(r * 0.8)
                pygame.draw.line(surface, color, (cx - off, cy - off), (cx + off, cy + off), 2)
                pygame.draw.line(surface, color, (cx + off, cy - off), (cx - off, cy + off), 2)
            elif req_type == "end":
                pygame.draw.circle(surface, color, (cx, cy), r, 1)
                pygame.draw.circle(surface, color, (cx, cy), r // 2)
            elif req_type == "visit":
                pygame.draw.circle(surface, color, (cx, cy), r)
            elif req_type == "consecutive":
                arc_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
                pygame.draw.arc(surface, color, arc_rect, 0.5, 5.8, 2)
                f = get_font(int(mini * 0.6), bold=True)
                ts = f.render(text.replace("⟳", ""), True, color)
                surface.blit(ts, ts.get_rect(center=(cx, cy)))
            else:
                display_text = text
                for prefix in ["⊘", "✓", "①", "$"]:
                    display_text = display_text.replace(prefix, "")
                
                if req_type == "avoid_step":
                    pygame.draw.circle(surface, color, (cx, cy), r, 1)
                    pygame.draw.line(surface, color, (cx - r + 2, cy + r - 2), (cx + r - 2, cy - r + 2), 2)
                elif req_type == "require_step":
                    pygame.draw.circle(surface, color, (cx, cy), r, 2)
                elif req_type == "order":
                    pygame.draw.circle(surface, color, (cx, cy), r, 1)
                
                current_font_size = font_size_base
                if len(display_text) > 2: 
                    current_font_size = int(mini * 0.45)
                
                font = get_font(current_font_size, bold=True)
                ts = font.render(display_text, True, color)
                surface.blit(ts, ts.get_rect(center=(cx, cy)))

def draw_global_requirements(surface, global_reqs, font, panel_x_start):
    y = 10
    for req in global_reqs:
        color = COLOR_GLOBAL_REQ if req["type"] == "steps" else (200, 200, 200)
        ts = font.render(req["text"], True, color)
        tr = ts.get_rect(topleft=(panel_x_start + 10, y))
        bg = tr.inflate(10, 6)
        bg.topleft = (panel_x_start + 5, y - 3)
        pygame.draw.rect(surface, (20, 20, 20), bg)
        pygame.draw.rect(surface, color, bg, 1)
        surface.blit(ts, tr)
        y += tr.height + 10

def draw_editor_indicator(surface, panel_x_start, panel_height):
    """Рисует индикатор режима редактирования."""
    try:
        font = pygame.font.SysFont("arial", 14, bold=True)
        hint_font = pygame.font.SysFont("arial", 11)
    except:
        font = pygame.font.Font(None, 16)
        hint_font = pygame.font.Font(None, 13)
    
    text = "EDITOR MODE"
    ts = font.render(text, True, COLOR_EDITOR_MODE)
    
    x = panel_x_start + 10
    y = panel_height - 60
    
    bg_rect = pygame.Rect(panel_x_start + 5, y - 5, SIDE_PANEL_WIDTH - 10, 50)
    pygame.draw.rect(surface, (30, 15, 30), bg_rect)
    pygame.draw.rect(surface, COLOR_EDITOR_MODE, bg_rect, 2)
    
    surface.blit(ts, (x, y))
    
    hint = hint_font.render("Enter - reload level", True, (180, 100, 180))
    surface.blit(hint, (x, y + 22))

def calculate_target_pos(start, ans_str, cols, rows):
    x, y = start
    mapping = {"u": (0, -1), "d": (0, 1), "l": (-1, 0), "r": (1, 0)}
    for move in ans_str.lower().split():
        if move[0] in mapping:
            dx, dy = mapping[move[0]]
            if 0 <= x + dx < cols and 0 <= y + dy < rows:
                x, y = x + dx, y + dy
    return (x, y)

def normalize_ans(ans_str):
    mapping = {"up": "u", "u": "u", "down": "d", "d": "d", "left": "l", "l": "l", "right": "r", "r": "r"}
    return [mapping[m] for m in ans_str.lower().split() if m in mapping]

# =============================================================================
# КОНСОЛЬ РАЗРАБОТЧИКА
# =============================================================================

def console_listener():
    print("\n[DEV] Консоль. F9+F11 для активации.")
    while game_running:
        try:
            cmd = input().strip().lower()
            if not game_running: break
            if not dev_access_granted:
                print("[LOCKED] F9+F11")
                continue
            
            if cmd == '1': print(f"ans: {' '.join(dev_recording)}\n")
            elif cmd == '2': dev_recording.clear(); print("[OK] Очищено\n")
            elif cmd == '3':
                global dev_show_coords
                dev_show_coords = not dev_show_coords
                print(f"[OK] Координаты: {'ВКЛ' if dev_show_coords else 'ВЫКЛ'}\n")
            elif cmd == '4':
                cell_map = {}
                for step, pos in enumerate(path_positions):
                    if pos not in cell_map: cell_map[pos] = []
                    cell_map[pos].append(step)
                print("\n=== КЛЕТКИ ===")
                for cell in sorted(cell_map.keys(), key=lambda k: (k[1], k[0])):
                    print(f"{cell[0]},{cell[1]}: {cell_map[cell]}")
                print("==============\n")
            elif cmd == '5':
                global dev_disable_victory
                dev_disable_victory = not dev_disable_victory
                print(f"[OK] Победа: {'ВЫКЛ' if dev_disable_victory else 'ВКЛ'}\n")
            elif cmd == 'help': print("\n1=SHOW 2=CLEAR 3=COORDS 4=CELLS 5=NOWIN\n")
        except EOFError:
            break

# =============================================================================
# ОСНОВНОЙ ЦИКЛ
# =============================================================================

def run_game(selected_idx, hints_enabled, edit_mode_enabled=False):
    global game_running, dev_recording, dev_access_granted, path_positions, dev_disable_victory
    global WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS
    global editor_mode, LEVELS

    editor_mode = edit_mode_enabled
    
    if not LEVELS:
        print("[CRITICAL] Нет уровней.")
        sys.exit(1)

    pygame.init()
    pygame.font.init()

    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    current_idx = selected_idx
    screen = None
    game_surface = None
    GRID_OFFSET_X = GRID_OFFSET_Y = 0
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
    
    state_manager = savestates.StateManager(max_history=200)

    console_thread = threading.Thread(target=console_listener, daemon=True)
    console_thread.start()

    def load_level(idx, clear_history=True):
        """
        Загружает уровень.
        clear_history=True  — полный сброс (Shift+R, новый уровень)
        clear_history=False — мягкий сброс (R, смерть) — история сохраняется
        """
        nonlocal player_pos, required_sequence, player_history, target_grid_pos
        nonlocal level_type, level_conditions, condition_cells, poison_data, walls_data
        nonlocal screen, game_surface, GRID_OFFSET_X, GRID_OFFSET_Y
        nonlocal show_requirements, level_requirements, global_requirements
        global dev_recording, path_positions
        global WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS

        lvl = LEVELS[idx]
        GRID_COLS, GRID_ROWS = lvl.get("grid", (16, 12))
        
        available_w = (screen_w * 0.85) - SIDE_PANEL_WIDTH
        max_h = screen_h * 0.85
        
        CELL_SIZE = int(min(available_w // GRID_COLS, max_h // GRID_ROWS))
        
        grid_w, grid_h = CELL_SIZE * GRID_COLS, CELL_SIZE * GRID_ROWS
        GRID_OFFSET_X = int(grid_w * 0.05)
        GRID_OFFSET_Y = int(grid_h * 0.05)
        
        WINDOW_WIDTH = grid_w + GRID_OFFSET_X * 2 + SIDE_PANEL_WIDTH
        WINDOW_HEIGHT = grid_h + GRID_OFFSET_Y * 2
        
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        game_surface = pygame.Surface((grid_w + 1, grid_h + 1), pygame.SRCALPHA)
        
        level_type = lvl.get("type", "sequence")
        player_pos = list(lvl["start"])
        player_history = []
        dev_recording.clear()
        path_positions = [tuple(player_pos)]
        
        # Очищаем историю только при полном ресете
        if clear_history:
            state_manager.reset()
            print("[RESET] Полный сброс (история очищена)")
        else:
            print(f"[RESET] Мягкий сброс (Z/L доступны, история: {len(state_manager.history)})")
        
        poison_data = lvl.get("poison", [])[:]
        walls_data = lvl.get("walls", [])[:]

        if lvl.get("wall_is_poison"):
            flag = lvl["wall_is_poison"]
            exceptions = [tuple(c) for c in flag.get("except", [])] if isinstance(flag, dict) else []
            new_walls = []
            for w in walls_data:
                if w[0] not in exceptions: poison_data.append(w)
                else: new_walls.append(w)
            walls_data = new_walls

        show_requirements = True
        level_requirements, global_requirements = get_condition_requirements(lvl, GRID_COLS, GRID_ROWS)
        
        if level_type == "sequence":
            required_sequence = normalize_ans(lvl.get("ans", ""))
            target_grid_pos = calculate_target_pos(lvl["start"], lvl.get("ans", ""), GRID_COLS, GRID_ROWS)
            level_conditions, condition_cells = [], []
        else:
            required_sequence, target_grid_pos = [], None
            level_conditions = lvl.get("conditions", [])
            condition_cells = get_condition_cells(lvl, GRID_COLS, GRID_ROWS)
        
        name = lvl.get("name", f"Уровень {idx + 1}")
        mode_prefix = "[EDIT] " if editor_mode else ""
        pygame.display.set_caption(f"{mode_prefix}{name} ({GRID_COLS}x{GRID_ROWS})")
        print(f"\n{'='*40}\n--- {mode_prefix}{name} ---\nТип: {level_type}")
        if hints_enabled and "hint" in lvl: print(f"Подсказка: {lvl['hint']}")
        print(f"{'='*40}\n")

    def reload_fonts():
        """Пересоздаёт шрифты после изменения размера сетки."""
        nonlocal font_steps, font_small, font_coords, font_req
        font_steps = pygame.font.SysFont("Arial", max(10, CELL_SIZE // 4))
        font_small = pygame.font.SysFont("Arial", max(8, CELL_SIZE // 5))
        font_coords = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 3), bold=True)
        font_req = pygame.font.SysFont("Arial", max(12, CELL_SIZE // 4), bold=True)

    load_level(current_idx, clear_history=True)
    
    font_steps = font_small = font_coords = font_req = None
    reload_fonts()

    while game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
            
            if event.type == pygame.KEYDOWN:
                keys = pygame.key.get_pressed()
                
                # Dev-режим
                if keys[pygame.K_F9] and keys[pygame.K_F11]:
                    dev_access_granted = True
                    print("\n[DEV] Активировано!\n")

                # R = мягкий ресет, Shift+R = полный ресет
                if event.key == pygame.K_r:
                    full_reset = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                    load_level(current_idx, clear_history=full_reset)
                    reload_fonts()
                    continue
                
                # X = показать/скрыть требования
                if event.key == pygame.K_x:
                    show_requirements = not show_requirements
                    continue
                
                # Enter в режиме редактора = перезагрузить файл
                if event.key == pygame.K_RETURN and editor_mode:
                    new_levels = editor.reload_edit_level(process_level_data)
                    if new_levels:
                        LEVELS = new_levels
                        current_idx = 0
                        load_level(current_idx, clear_history=True)
                        reload_fonts()
                    continue
                
                # S = ручное сохранение
                if event.key == pygame.K_s:
                    state_manager.save_manual(player_pos, path_positions, player_history, dev_recording)
                    continue

                # L = загрузка ручного сохранения
                if event.key == pygame.K_l:
                    data = state_manager.load_manual()
                    if data:
                        player_pos = data['pos']
                        path_positions = data['path']
                        player_history = data['hist']
                        dev_recording = data['dev']
                        # ИСПРАВЛЕНИЕ: обновляем режим просмотра
                        if len(path_positions) > 1:
                            show_requirements = False
                    continue

                # Z = откат на один шаг
                if event.key == pygame.K_z:
                    data = state_manager.pop()
                    if data:
                        player_pos = data['pos']
                        path_positions = data['path']
                        player_history = data['hist']
                        dev_recording = data['dev']
                        # ИСПРАВЛЕНИЕ: обновляем режим просмотра
                        if len(path_positions) > 1:
                            show_requirements = False
                    else:
                        print("[UNDO] История пуста")
                    continue

                # Обработка движения
                dx, dy, move = 0, 0, None
                if event.key == pygame.K_UP:    dx, dy, move = 0, -1, "u"
                elif event.key == pygame.K_DOWN:  dx, dy, move = 0, 1, "d"
                elif event.key == pygame.K_LEFT:  dx, dy, move = -1, 0, "l"
                elif event.key == pygame.K_RIGHT: dx, dy, move = 1, 0, "r"

                if move:
                    if show_requirements and len(path_positions) == 1:
                        show_requirements = False
                    
                    target = [player_pos[0] + dx, player_pos[1] + dy]
                    in_bounds = 0 <= target[0] < GRID_COLS and 0 <= target[1] < GRID_ROWS
                    hit_poison = not is_path_clear(player_pos, target, poison_data)
                    blocked = not is_path_clear(player_pos, target, walls_data)

                    # ИСПРАВЛЕНИЕ: сохраняем состояние ПЕРЕД смертью
                    if hit_poison:
                        state_manager.push(player_pos, path_positions, player_history, dev_recording)
                        print("☠ ПОГИБ! (Z = откат на ход до смерти, L = загрузка)")
                        load_level(current_idx, clear_history=False)
                        continue


                    if in_bounds and not blocked:
                        state_manager.push(player_pos, path_positions, player_history, dev_recording)
                        player_pos = target

                    player_history.append(move)
                    dev_recording.append(move)
                    path_positions.append(tuple(player_pos))

                    # Проверка победы
                    complete = False
                    if level_type == "sequence":
                        if player_history == required_sequence:
                            complete = True
                        elif len(player_history) >= len(required_sequence) and hints_enabled:
                            print("Неверно! R")
                    else:
                        if check_all_conditions(level_conditions, path_positions, player_pos, GRID_COLS, GRID_ROWS):
                            complete = True
                    
                    if complete:
                        if dev_disable_victory:
                            print("[DEV] Победа OFF")
                        else:
                            print(f"✓ Уровень {current_idx + 1} пройден!")
                            
                            if editor_mode:
                                print("[EDITOR] Пройдено! R = сброс, Enter = перезагрузка файла")
                            else:
                                current_idx += 1
                                if current_idx < len(LEVELS):
                                    load_level(current_idx, clear_history=True)
                                    reload_fonts()
                                else:
                                    print("\n🎉 ИГРА ПРОЙДЕНА! 🎉")
                                    game_running = False

        # === ОТРИСОВКА ===
        screen.fill(COLOR_BG)
        game_surface.fill(COLOR_BG)
        
        if level_type == "condition":
            for cell in condition_cells:
                pygame.draw.rect(game_surface, COLOR_CONDITION_HINT,
                    (cell[0] * CELL_SIZE, cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE))

        if level_type == "sequence" and target_grid_pos:
            pygame.draw.rect(game_surface, COLOR_TARGET,
                (target_grid_pos[0] * CELL_SIZE, target_grid_pos[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE))

        draw_grid(game_surface, GRID_COLS * CELL_SIZE, GRID_ROWS * CELL_SIZE, CELL_SIZE)
        draw_barriers(game_surface, walls_data, COLOR_WALL, CELL_SIZE)
        draw_barriers(game_surface, poison_data, COLOR_POISON, CELL_SIZE)

        # Отрисовка номеров шагов (если требования скрыты)
        if not (show_requirements and (level_requirements or global_requirements)):
            cell_data = {}
            for step, pos in enumerate(path_positions):
                if pos not in cell_data: cell_data[pos] = []
                if len(cell_data[pos]) < 9: cell_data[pos].append(step)
            for pos, steps in cell_data.items():
                for i, val in enumerate(steps):
                    f = get_font(max(8, CELL_SIZE // 7)) if val >= 100 else get_font(max(10, CELL_SIZE // 5))
                    ts = f.render(str(val), True, COLOR_TEXT)
                    game_surface.blit(ts, (pos[0] * CELL_SIZE + 2 + (i % 3) * (CELL_SIZE // 3),
                                           pos[1] * CELL_SIZE + 2 + (i // 3) * (CELL_SIZE // 3)))

        # Игрок
        px = player_pos[0] * CELL_SIZE + CELL_SIZE // 2
        py = player_pos[1] * CELL_SIZE + CELL_SIZE // 2
        pygame.draw.circle(game_surface, COLOR_PLAYER, (px, py), int(CELL_SIZE * 0.4))

        # Требования на клетках
        if show_requirements and level_requirements:
            draw_requirements(game_surface, level_requirements, CELL_SIZE)

        # Dev-координаты
        if dev_show_coords:
            f_coords = get_font(max(12, CELL_SIZE // 3), bold=True)
            for gy in range(GRID_ROWS):
                for gx in range(GRID_COLS):
                    ts = f_coords.render(f"{gx},{gy}", True, COLOR_DEV_COORDS)
                    game_surface.blit(ts, ((gx + 1) * CELL_SIZE - ts.get_width() - 3,
                                           (gy + 1) * CELL_SIZE - ts.get_height() - 3))

        screen.blit(game_surface, (GRID_OFFSET_X, GRID_OFFSET_Y))

        # Глобальные требования на панели
        if show_requirements and global_requirements:
            panel_x = WINDOW_WIDTH - SIDE_PANEL_WIDTH
            draw_global_requirements(screen, global_requirements, 
                                     get_font(max(12, CELL_SIZE // 4), bold=True), 
                                     panel_x)

        # Индикатор режима редактирования
        if editor_mode:
            panel_x = WINDOW_WIDTH - SIDE_PANEL_WIDTH
            draw_editor_indicator(screen, panel_x, WINDOW_HEIGHT)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("          GRID PUZZLE GAME")
    print("=" * 50)
    
    print("\nВыберите режим:")
    print("  1 - Загрузить levels.json (основные уровни)")
    print("  2 - Загрузить user_levels.json (пользовательские)")
    print("  3 - Режим редактирования (edit_user_level.json)")
    print()
    
    mode = input("Ваш выбор (1/2/3): ").strip()
    
    edit_mode = False
    
    if mode == "3":
        edit_mode = True
        editor.print_editor_help()
        
        LEVELS = editor.reload_edit_level(process_level_data)
        if not LEVELS:
            print("\n[EDITOR] Создан шаблон. Отредактируйте edit_user_level.json и перезапустите.")
            LEVELS = editor.reload_edit_level(process_level_data)
        
        if LEVELS:
            hints = True
            run_game(0, hints, edit_mode_enabled=True)
        else:
            print("[ERROR] Не удалось загрузить уровень для редактирования.")
            sys.exit(1)
    
    elif mode == "2":
        if os.path.exists("user_levels.json"):
            LEVELS = load_levels_from_file("user_levels.json", is_internal=False)
        if not LEVELS:
            print("[ERROR] user_levels.json не найден или пуст. Загружаю levels.json...")
            LEVELS = load_levels_from_file("levels.json", is_internal=True)
    
    else:
        LEVELS = load_levels_from_file("levels.json", is_internal=True)

    if not edit_mode:
        if not LEVELS:
            print("Ошибка: нет уровней.")
            sys.exit(1)

        hints = input("Подсказки? (y): ").strip().lower() in ("да", "yes", "y")
        
        print(f"\nУровней: {len(LEVELS)}")
        for i, lvl in enumerate(LEVELS):
            t = "SEQ" if lvl.get("type") == "sequence" else "COND"
            print(f"  {i+1}. [{t}] {lvl.get('name', f'Уровень {i+1}')}")
        
        try:
            choice = input(f"\nВыбор (1-{len(LEVELS)}): ").strip()
            idx = int(choice) - 1 if choice else 0
            run_game(max(0, min(idx, len(LEVELS) - 1)), hints)
        except ValueError:
            run_game(0, hints)
