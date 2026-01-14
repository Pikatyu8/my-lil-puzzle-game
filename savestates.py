import copy

class StateManager:
    def __init__(self, max_history=500): # Увеличил лимит, так как история координат важнее
        self.history = []
        self.manual_slot = None
        self.max_history = max_history

    def push(self, player_pos, path_positions, player_history, dev_recording):
        """Сохраняет текущее состояние в историю для Undo (Z)."""
        # Используем deepcopy, чтобы создать полную, независимую копию списка координат.
        # Это гарантирует, что при нажатии Z мы вернемся к ТОЧНОМУ списку посещений,
        # который был на тот момент, включая все повторные заходы на клетку.
        state = {
            'pos': list(player_pos),          # Где стоит игрок
            'path': copy.deepcopy(path_positions), # Вся история перемещений (включая повторы!)
            'hist': list(player_history),     # История нажатий клавиш
            'dev': list(dev_recording),       # Для дебага
            'step_count': len(path_positions) # Номер хода (как ты и просил)
        }
        
        self.history.append(state)
        
        # Если история слишком длинная, удаляем самые старые записи
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def pop(self):
        """Возвращает предыдущее состояние и удаляет его из истории."""
        if not self.history:
            return None
        
        # pop() достает последнее состояние.
        # Так как мы использовали deepcopy при сохранении,
        # этот список 'path' будет на 1 элемент короче текущего,
        # и визуально ты откатишься ровно на 1 цифру назад.
        return self.history.pop()

    def save_manual(self, player_pos, path_positions, player_history, dev_recording):
        """Сохраняет состояние в слот 'S'."""
        self.manual_slot = {
            'pos': list(player_pos),
            'path': copy.deepcopy(path_positions),
            'hist': list(player_history),
            'dev': list(dev_recording),
            'step_count': len(path_positions)
        }
        print(f"[SAVE] Сохранено на ходу: {len(path_positions)}")

    def load_manual(self):
        """Загружает состояние из слота 'S'."""
        if not self.manual_slot:
            print("[LOAD] Нет сохранений")
            return None
        print(f"[LOAD] Загрузка хода: {self.manual_slot.get('step_count', '?')}")
        # Возвращаем копию, чтобы загрузка не испортила сам слот сохранения
        return copy.deepcopy(self.manual_slot)

    def reset(self):
        self.history.clear()
        self.manual_slot = None
