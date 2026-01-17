"""
Модуль для работы с двигаемыми объектами (коробками).
Поддержка связанных групп через "connected": true.
"""

import pygame

COLOR_MOVABLE = (255, 165, 0)  # Оранжевый
COLOR_MOVABLE_BORDER = (200, 130, 0)
COLOR_BLOCKED_MARK = (255, 50, 50)
COLOR_GROUP_LINK = (180, 120, 40)  # Цвет связей между объектами группы


class MovableObject:
    """Представляет один двигаемый объект."""
    
    def __init__(self, pos, blocked=None, can_push=True, can_be_pushed_by=True, group_id=None):
        """
        Args:
            pos: позиция (x, y)
            blocked: стороны, с которых нельзя толкать ("u", "d", "l", "r")
            can_push: может ли этот объект толкать другие
            can_be_pushed_by: может ли быть сдвинут другим объектом (не игроком!)
            group_id: ID группы для connected объектов (None = не в группе)
        """
        self.pos = tuple(pos)
        self.blocked = set(blocked) if blocked else set()
        self.can_push = can_push
        self.can_be_pushed_by = can_be_pushed_by
        self.group_id = group_id
    
    def copy(self):
        """Создаёт копию объекта."""
        return MovableObject(
            self.pos, 
            self.blocked.copy(), 
            self.can_push, 
            self.can_be_pushed_by,
            self.group_id
        )


class MovableManager:
    """Управляет всеми двигаемыми объектами на уровне."""
    
    SIDE_MAP = {
        'u': 'up', 'd': 'down', 'l': 'left', 'r': 'right',
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'
    }
    
    OPPOSITE = {
        'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'
    }
    
    DIRECTION_DELTA = {
        'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)
    }
    
    MOVE_TO_DIR = {
        'u': 'up', 'd': 'down', 'l': 'left', 'r': 'right'
    }
    
    def __init__(self):
        self.objects = {}  # pos -> MovableObject
        self.initial_objects = {}  # для сброса уровня
    
    def copy_state(self):
        """Создаёт копию текущего состояния для undo/save."""
        return {pos: obj.copy() for pos, obj in self.objects.items()}
    
    def restore_state(self, state):
        """Восстанавливает состояние из копии."""
        if state is None:
            self.objects = {}
            return
        self.objects = {pos: obj.copy() for pos, obj in state.items()}
    
    def reset(self):
        """Сбрасывает позиции объектов к начальным."""
        self.objects = {pos: obj.copy() for pos, obj in self.initial_objects.items()}
    
    def clear(self):
        """Полностью очищает менеджер."""
        self.objects.clear()
        self.initial_objects.clear()
    
    def add_object(self, pos, blocked=None, can_push=True, can_be_pushed_by=True, group_id=None):
        """Добавляет объект."""
        pos = tuple(pos)
        obj = MovableObject(pos, blocked, can_push, can_be_pushed_by, group_id)
        self.objects[pos] = obj
        self.initial_objects[pos] = obj.copy()
    
    def get_at(self, pos):
        """Возвращает объект в позиции или None."""
        return self.objects.get(tuple(pos))
    
    def has_object_at(self, pos):
        """Проверяет наличие объекта в позиции."""
        return tuple(pos) in self.objects
    
    def get_group_positions(self, group_id):
        """Возвращает все текущие позиции объектов группы."""
        if group_id is None:
            return set()
        return {pos for pos, obj in self.objects.items() if obj.group_id == group_id}
    
    def try_push(self, player_pos, move_char, grid_cols, grid_rows, 
                 walls_data, poison_data, is_path_clear_func):
        """
        Пытается выполнить ход игрока с учётом толкания объектов.
        
        Returns:
            dict с результатами
        """
        result = {
            'can_move': False,
            'hit_poison': False,
            'blocked_by_wall': False,
            'blocked_by_box': False,
            'out_of_bounds': False,
            'moves_made': [],
            'target_pos': None
        }
        
        direction = self.MOVE_TO_DIR.get(move_char)
        if not direction:
            return result
        
        dx, dy = self.DIRECTION_DELTA[direction]
        target_pos = (player_pos[0] + dx, player_pos[1] + dy)
        result['target_pos'] = target_pos
        
        # Проверяем границы
        if not (0 <= target_pos[0] < grid_cols and 0 <= target_pos[1] < grid_rows):
            result['out_of_bounds'] = True
            return result
        
        # Проверяем яд для игрока
        if not is_path_clear_func(tuple(player_pos), target_pos, poison_data):
            result['hit_poison'] = True
            return result
        
        # Проверяем стены для игрока
        if not is_path_clear_func(tuple(player_pos), target_pos, walls_data):
            result['blocked_by_wall'] = True
            return result
        
        # Проверяем объект в целевой позиции
        obj = self.get_at(target_pos)
        if not obj:
            result['can_move'] = True
            return result
        
        # Проверяем заблокированную сторону
        push_side = self.OPPOSITE[direction]
        if push_side in obj.blocked:
            result['blocked_by_box'] = True
            return result
        
        # Если объект в группе - толкаем всю группу
        if obj.group_id is not None:
            return self._try_push_group(
                obj.group_id, target_pos, direction, grid_cols, grid_rows,
                walls_data, poison_data, is_path_clear_func
            )
        
        # Иначе обычная логика с цепочкой
        chain = self._collect_push_chain(
            target_pos, direction, grid_cols, grid_rows,
            walls_data, poison_data, is_path_clear_func
        )
        
        if chain is None:
            result['blocked_by_box'] = True
            return result
        
        # Выполняем перемещение (с конца цепочки)
        moves = []
        for old_pos in reversed(chain):
            obj = self.objects.pop(old_pos)
            new_pos = (old_pos[0] + dx, old_pos[1] + dy)
            obj.pos = new_pos
            self.objects[new_pos] = obj
            moves.append((old_pos, new_pos))
        
        result['can_move'] = True
        result['moves_made'] = moves
        return result
    
    def _try_push_group(self, group_id, touched_pos, direction, cols, rows,
                        walls_data, poison_data, is_path_clear_func):
        """Пытается толкнуть связанную группу объектов как единое целое."""
        result = {
            'can_move': False,
            'hit_poison': False,
            'blocked_by_wall': False,
            'blocked_by_box': False,
            'out_of_bounds': False,
            'moves_made': [],
            'target_pos': touched_pos
        }
        
        dx, dy = self.DIRECTION_DELTA[direction]
        group_positions = self.get_group_positions(group_id)
        
        # Проверяем каждый объект группы
        for pos in group_positions:
            new_pos = (pos[0] + dx, pos[1] + dy)
            
            # Границы
            if not (0 <= new_pos[0] < cols and 0 <= new_pos[1] < rows):
                result['out_of_bounds'] = True
                result['blocked_by_box'] = True
                return result
            
            # Стены
            if not is_path_clear_func(pos, new_pos, walls_data):
                result['blocked_by_wall'] = True
                result['blocked_by_box'] = True
                return result
            
            # Яд
            if not is_path_clear_func(pos, new_pos, poison_data):
                result['blocked_by_box'] = True
                return result
            
            # Другой объект (не из нашей группы)
            target_obj = self.get_at(new_pos)
            if target_obj and new_pos not in group_positions:
                result['blocked_by_box'] = True
                return result
        
        # Перемещаем всю группу атомарно
        moves = []
        moved_objects = {}
        
        for pos in group_positions:
            obj = self.objects.pop(pos)
            new_pos = (pos[0] + dx, pos[1] + dy)
            obj.pos = new_pos
            moved_objects[new_pos] = obj
            moves.append((pos, new_pos))
        
        self.objects.update(moved_objects)
        
        result['can_move'] = True
        result['moves_made'] = moves
        return result
    
    def _collect_push_chain(self, start_pos, direction, cols, rows, 
                            walls_data, poison_data, is_path_clear_func):
        """
        Собирает цепочку одиночных объектов для перемещения.
        Группы не могут быть частью цепочки.
        """
        dx, dy = self.DIRECTION_DELTA[direction]
        chain = []
        current_pos = start_pos
        push_side = self.OPPOSITE[direction]
        
        while True:
            obj = self.get_at(current_pos)
            if not obj:
                break
            
            # Группы нельзя толкать через цепочку
            if obj.group_id is not None and current_pos != start_pos:
                return None
            
            chain.append(current_pos)
            next_pos = (current_pos[0] + dx, current_pos[1] + dy)
            
            # Проверяем границы
            if not (0 <= next_pos[0] < cols and 0 <= next_pos[1] < rows):
                return None
            
            # Проверяем стены
            if not is_path_clear_func(current_pos, next_pos, walls_data):
                return None
            
            # Проверяем яд
            if not is_path_clear_func(current_pos, next_pos, poison_data):
                return None
            
            # Проверяем следующий объект
            next_obj = self.get_at(next_pos)
            if next_obj:
                # Нельзя толкать группу как часть цепочки
                if next_obj.group_id is not None:
                    return None
                
                if not obj.can_push:
                    return None
                
                if not next_obj.can_be_pushed_by:
                    return None
                
                if push_side in next_obj.blocked:
                    return None
            
            current_pos = next_pos
        
        return chain if chain else None
    
    def get_all_positions(self):
        """Возвращает все позиции объектов."""
        return list(self.objects.keys())
    
    def is_empty(self):
        """Проверяет, есть ли объекты."""
        return len(self.objects) == 0
    
    def get_groups(self):
        """Возвращает словарь {group_id: [positions]}."""
        groups = {}
        for pos, obj in self.objects.items():
            if obj.group_id is not None:
                if obj.group_id not in groups:
                    groups[obj.group_id] = []
                groups[obj.group_id].append(pos)
        return groups


# =============================================================================
# ПАРСИНГ
# =============================================================================

def parse_blocked_sides(blocked_raw):
    """Парсит заблокированные стороны."""
    SIDE_MAP = {
        'u': 'up', 'd': 'down', 'l': 'left', 'r': 'right',
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'
    }
    
    if not blocked_raw:
        return []
    
    if isinstance(blocked_raw, str):
        result = []
        for c in blocked_raw.lower():
            if c in SIDE_MAP:
                result.append(SIDE_MAP[c])
        return result
    
    if isinstance(blocked_raw, list):
        result = []
        for b in blocked_raw:
            if isinstance(b, str):
                b_lower = b.lower()
                if b_lower in SIDE_MAP:
                    result.append(SIDE_MAP[b_lower])
        return result
    
    return []


def generate_rect_cells(start, end):
    """Генерирует все клетки в прямоугольнике."""
    x1, y1 = int(start[0]), int(start[1])
    x2, y2 = int(end[0]), int(end[1])
    return [
        (x, y)
        for x in range(min(x1, x2), max(x1, x2) + 1)
        for y in range(min(y1, y2), max(y1, y2) + 1)
    ]


def parse_movable_data(movable_list):
    """
    Парсит данные о movable объектах из JSON.
    """
    manager = MovableManager()
    
    if not movable_list:
        return manager
    
    group_counter = 0
    
    for item in movable_list:
        if not isinstance(item, dict):
            continue
        
        blocked = parse_blocked_sides(item.get("blocked", []))
        can_push = item.get("can_push", True)
        can_be_pushed_by = item.get("can_be_pushed_by", True)
        connected = item.get("connected", False)
        
        # Генерируем group_id если connected
        group_id = None
        if connected:
            group_counter += 1
            group_id = group_counter
        
        # Собираем все ячейки
        cells = []
        
        if "cell" in item:
            c = item["cell"]
            cells.append((int(c[0]), int(c[1])))
        
        if "cells" in item:
            for c in item["cells"]:
                cells.append((int(c[0]), int(c[1])))
        
        if "range" in item:
            r = item["range"]
            cells.extend(generate_rect_cells(r[0], r[1]))
        
        if "ranges" in item:
            for r in item["ranges"]:
                cells.extend(generate_rect_cells(r[0], r[1]))
        
        # Добавляем объекты
        for cell in cells:
            manager.add_object(cell, blocked, can_push, can_be_pushed_by, group_id)
    
    return manager


# =============================================================================
# ОТРИСОВКА (ОБНОВЛЕННАЯ С ЗАТЕМНЕНИЕМ)
# =============================================================================

def dim_color(color, factor=0.4):
    """
    Затемняет цвет, сохраняя его оттенок.
    Factor: 1.0 = оригинал, 0.5 = в два раза темнее, 0.0 = черный.
    Игнорирует alpha, возвращает (R, G, B).
    """
    r, g, b = color[:3]
    return (
        max(0, int(r * factor)),
        max(0, int(g * factor)),
        max(0, int(b * factor))
    )

def _are_neighbors(pos1, pos2):
    """Проверяет, являются ли позиции соседями (по горизонтали/вертикали)."""
    dx = abs(pos1[0] - pos2[0])
    dy = abs(pos1[1] - pos2[1])
    return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)


def draw_movable_objects(surface, manager, cell_size, dim=False):
    """
    Отрисовывает все movable объекты.
    
    Args:
        surface: поверхность для рисования
        manager: MovableManager
        cell_size: размер клетки
        dim: если True, цвета будут затемнены (для режима просмотра условий)
    """
    if manager.is_empty():
        return
    
    # Коэффициент яркости (1.0 = норма, 0.4 = темно)
    factor = 0.4 if dim else 1.0
    
    # Предварительно вычисляем цвета
    c_movable = dim_color(COLOR_MOVABLE, factor)
    c_border = dim_color(COLOR_MOVABLE_BORDER, factor)
    c_mark = dim_color(COLOR_BLOCKED_MARK, factor)
    c_link = dim_color(COLOR_GROUP_LINK, factor)
    
    # Получаем группы для отрисовки связей
    groups = manager.get_groups()
    
    # Рисуем связи между соседними объектами групп
    for group_id, positions in groups.items():
        if len(positions) > 1:
            for i, pos1 in enumerate(positions):
                for pos2 in positions[i+1:]:
                    if _are_neighbors(pos1, pos2):
                        x1 = pos1[0] * cell_size + cell_size // 2
                        y1 = pos1[1] * cell_size + cell_size // 2
                        x2 = pos2[0] * cell_size + cell_size // 2
                        y2 = pos2[1] * cell_size + cell_size // 2
                        pygame.draw.line(surface, c_link, (x1, y1), (x2, y2), 4)
    
    # Рисуем сами объекты
    for pos in manager.get_all_positions():
        x, y = pos
        px = x * cell_size + cell_size // 2
        py = y * cell_size + cell_size // 2
        
        obj = manager.get_at(pos)
        size = int(cell_size * 0.7)
        half = size // 2
        
        # Основной прямоугольник
        rect = pygame.Rect(px - half, py - half, size, size)
        pygame.draw.rect(surface, c_movable, rect)
        
        # Рамка
        border_width = 4 if (obj and not obj.can_be_pushed_by) else 2
        pygame.draw.rect(surface, c_border, rect, border_width)
        
        if obj:
            # Индикатор группы (маленький круг в углу)
            if obj.group_id is not None:
                indicator_r = size // 6
                indicator_x = px + half - indicator_r - 2
                indicator_y = py - half + indicator_r + 2
                pygame.draw.circle(surface, c_link, 
                                  (indicator_x, indicator_y), indicator_r)
            
            # Индикатор заблокированных сторон
            mark_len = size // 3
            mark_thick = 3
            
            if 'up' in obj.blocked:
                pygame.draw.rect(surface, c_mark, 
                    (px - mark_len//2, py - half - mark_thick, mark_len, mark_thick))
            if 'down' in obj.blocked:
                pygame.draw.rect(surface, c_mark,
                    (px - mark_len//2, py + half, mark_len, mark_thick))
            if 'left' in obj.blocked:
                pygame.draw.rect(surface, c_mark,
                    (px - half - mark_thick, py - mark_len//2, mark_thick, mark_len))
            if 'right' in obj.blocked:
                pygame.draw.rect(surface, c_mark,
                    (px + half, py - mark_len//2, mark_thick, mark_len))
            
            # Не может толкать - X внутри
            if not obj.can_push:
                cross_size = size // 4
                pygame.draw.line(surface, c_border,
                    (px - cross_size, py - cross_size), 
                    (px + cross_size, py + cross_size), 2)
                pygame.draw.line(surface, c_border,
                    (px + cross_size, py - cross_size), 
                    (px - cross_size, py + cross_size), 2)
