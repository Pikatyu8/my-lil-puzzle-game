from src.movable.movement import collect_push_chain, try_push_group


class MovableObject:
    """Представляет один двигаемый объект."""

    def __init__(self, pos, blocked=None, can_push=True, can_be_pushed_by=True, group_id=None):
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
        self.objects = {}
        self.initial_objects = {}

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

        if not (0 <= target_pos[0] < grid_cols and 0 <= target_pos[1] < grid_rows):
            result['out_of_bounds'] = True
            return result

        if not is_path_clear_func(tuple(player_pos), target_pos, poison_data):
            result['hit_poison'] = True
            return result

        if not is_path_clear_func(tuple(player_pos), target_pos, walls_data):
            result['blocked_by_wall'] = True
            return result

        obj = self.get_at(target_pos)
        if not obj:
            result['can_move'] = True
            return result

        push_side = self.OPPOSITE[direction]
        if push_side in obj.blocked:
            result['blocked_by_box'] = True
            return result

        if obj.group_id is not None:
            return try_push_group(
                self, obj.group_id, target_pos, direction, grid_cols, grid_rows,
                walls_data, poison_data, is_path_clear_func
            )

        chain = collect_push_chain(
            self, target_pos, direction, grid_cols, grid_rows,
            walls_data, poison_data, is_path_clear_func
        )

        if chain is None:
            result['blocked_by_box'] = True
            return result

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
