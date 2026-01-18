import json
import os

EDIT_FILE = "edit_user_level.json"


def load_edit_level(filename=EDIT_FILE):
    """Загружает уровень из файла редактирования."""
    try:
        if not os.path.exists(filename):
            print(f"[EDITOR] Файл {filename} не найден. Создаю шаблон...")
            create_template(filename)
            return load_edit_level(filename)

        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        print(f"[EDITOR] Загружено уровней: {len(data)}")
        return data

    except json.JSONDecodeError as e:
        print(f"[EDITOR] ❌ Ошибка JSON: {e}")
        print(f"[EDITOR] Проверьте синтаксис файла {filename}")
        return None
    except Exception as e:
        print(f"[EDITOR] ❌ Ошибка загрузки: {e}")
        return None


def create_template(filename=EDIT_FILE):
    """Создаёт шаблон файла уровня с примерами."""
    template = """{
  "name": "Полный пример",
  "type": "condition",
  "grid": [10, 11],
  "start": [0, 0],
  "conditions": [
    {"check": "total_steps", "count": 136, "operator": ">="},
    
    {"check": "no_revisit", "except": [
      [0,1], [0,2], [5,4], [6,4], [2,6], [2,7], [5,5], [4,7], [4,8], [5,7], [5,8]
    ]},
    {"check": "order", "cells": [[0,2], [4,0], [7,2], [7,1], [6,1], [6,2]]},
    
    {"check": "visit", "cells": [[8,1], [3,5], [4,5]], "count": 0, "operator": "=="},
    {"check": "visit", "cells": [[5,4]], "count": 8, "operator": "=="},
    {"check": "visit", "cells": [[6,4]], "count": 7, "operator": "=="},
    {"check": "visit", "cells": [[5,5]], "count": 2, "operator": "=="},
    {"check": "visit", "cells": [[2,6], [2,7]], "count": 2, "operator": "=="},
    {"check": "visit", "cells": [[4,7], [4,8], [5,7], [5,8]], "count": 5, "operator": "=="},
    
    {"check": "visit", "cells": [[9,10]]},
    {"check": "visit", "cells": [[2,8]], "count": 1, "operator": "=="},
    
    {"check": "consecutive", "cells": [[0,1], [0,2]], "count": 3}
  ],
  
  "movable": [
    {"range": [[2, 8], [3, 8]], "blocked": "u", "connected":"true"}
    ],

  "walls": [
    {"cells": [[4,0], [4,1], [4,2]], "sides": "r", "type": "both"}
  ],
  
  "poison": [
    {"range": [[0,5], [9,10]], "mode": "perimeter", "sides": "ldr", "type": "both"},
    
    {"range": [[5,5], [9,7]],  "sides": "dr", "type": "outer"},
    {"range": [[5,8], [9,10]], "sides": "dl", "type": "outer"},
    {"range": [[0,8], [4,10]], "sides": "ul", "type": "outer"},
    {"range": [[0,5], [4,7]],  "sides": "ur", "type": "outer"},
    
    {"cells": [[0,2], [1,2], [3,2], [4,2]], "sides": "d", "type": "both"},
    {"cell": [2,2], "sides": "d", "type": "outer"},
    
    {"range": [[5,5], [9,5]], "sides": "u", "type": "inner"}
  ],
  
  "hint": ""
}
"""

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(template)
        print(f"[EDITOR] Шаблон создан: {filename}")
        print(f"[EDITOR] Отредактируйте файл и нажмите Enter в игре для перезагрузки")
    except Exception as e:
        print(f"[EDITOR] Ошибка создания шаблона: {e}")
