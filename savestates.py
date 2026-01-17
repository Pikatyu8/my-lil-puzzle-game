import copy

class StateManager:
    def __init__(self, max_history=500):
        self.history = []
        self.manual_slot = None
        self.max_history = max_history

    def push(self, player_pos, path_positions, player_history, dev_recording, movable_state=None):
            state = {
                'pos': list(player_pos),
                'path': copy.deepcopy(path_positions),
                'hist': list(player_history),
                'dev': list(dev_recording),
                # ИЗМЕНЕНО: проверка на is not None вместо простого if
                'movable': copy.deepcopy(movable_state) if movable_state is not None else None,
                'step_count': len(path_positions)
            }
            self.history.append(state)
            if len(self.history) > self.max_history:
                self.history.pop(0)

    def pop(self):
        if not self.history:
            return None
        return self.history.pop()

    def save_manual(self, player_pos, path_positions, player_history, dev_recording, movable_state=None):
        self.manual_slot = {
            'pos': list(player_pos),
            'path': copy.deepcopy(path_positions),
            'hist': list(player_history),
            'dev': list(dev_recording),
            # ИЗМЕНЕНО: проверка на is not None
            'movable': copy.deepcopy(movable_state) if movable_state is not None else None,
            'step_count': len(path_positions)
        }
        print(f"[SAVE] Сохранено на ходу: {len(path_positions)}")

    def load_manual(self):
        if not self.manual_slot:
            return None
        return copy.deepcopy(self.manual_slot)

    def reset(self):
        self.history.clear()
        self.manual_slot = None
