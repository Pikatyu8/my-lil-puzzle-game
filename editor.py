import json
import os
import pygame

EDIT_FILE = "edit_user_level.json"

def load_edit_level(filename=EDIT_FILE):
    """Загружает уровень из файла редактирования."""
    try:
        if not os.path.exists(filename):
            print(f"[EDITOR] Файл {filename} не найден. Создаю шаблон...")
            create_template(filename)
            return load_edit_level(filename)  # Рекурсивно загружаем созданный шаблон
        
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Если это одиночный уровень (словарь), оборачиваем в список
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
    # Записываем как строку для красивого форматирования
    template = """{
      "name": "Полный пример",
      "type": "condition",
      "grid": [10, 8],
      "start": [0, 0],
      "conditions": [
        {"check": "visit", "cells": [[5, 4]], "count": 8, "operator": "=="},
        {"check": "end_at", "cells": [[9, 7]]}
      ],
      "walls": [
        [[[4, 0], [4, 1], [4, 2]], {"r": "both"}]
      ],
      "poison": [
        [[[0, 2],[1, 2],[2, 2],[3, 2],[4, 2]], {"d": "outer"}]
      ],
      "hint": "Посети центр дважды, избегай яда"
}
"""
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(template)
        print(f"[EDITOR] Шаблон создан: {filename}")
        print(f"[EDITOR] Отредактируйте файл и нажмите Enter в игре для перезагрузки")
    except Exception as e:
        print(f"[EDITOR] Ошибка создания шаблона: {e}")

def validate_level(level_data):
    """Базовая валидация уровня."""
    errors = []
    warnings = []
    
    # Обязательные поля
    if "start" not in level_data:
        errors.append("Отсутствует поле 'start'")
    
    if "grid" not in level_data:
        warnings.append("Нет 'grid', используется 16x12 по умолчанию")
    
    level_type = level_data.get("type", "sequence")
    
    if level_type == "sequence":
        if "ans" not in level_data:
            errors.append("Для type='sequence' требуется поле 'ans'")
    elif level_type == "condition":
        if "conditions" not in level_data:
            errors.append("Для type='condition' требуется поле 'conditions'")
    else:
        warnings.append(f"Неизвестный тип уровня: {level_type}")
    
    # Проверка start в пределах grid
    if "start" in level_data and "grid" in level_data:
        sx, sy = level_data["start"]
        gx, gy = level_data["grid"]
        if not (0 <= sx < gx and 0 <= sy < gy):
            errors.append(f"start {level_data['start']} вне grid {level_data['grid']}")
    
    # Вывод результатов
    if errors:
        print("[EDITOR] ❌ ОШИБКИ:")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print("[EDITOR] ⚠ ПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print(f"  - {w}")
    
    if not errors and not warnings:
        print("[EDITOR] ✓ Валидация пройдена")
    
    return len(errors) == 0


def reload_edit_level(process_func):
    """
    Перезагружает уровень из файла и обрабатывает его.
    process_func - функция process_level_data из game.py
    """
    print("\n" + "=" * 40)
    print("[EDITOR] Перезагрузка уровня...")
    print("=" * 40)
    
    data = load_edit_level()
    if data is None:
        return None
    
    # Удаляем служебные поля
    for level in data:
        level.pop("_comment", None)
        level.pop("_examples", None)
        level.pop("_note", None)
    
    # Валидация
    for i, level in enumerate(data):
        print(f"\n[EDITOR] Проверка уровня {i + 1}: {level.get('name', 'Без имени')}")
        if not validate_level(level):
            print("[EDITOR] ❌ Уровень содержит ошибки!")
            return None
    
    # Обработка данных (walls, poison и т.д.)
    try:
        processed = process_func(data)
        print(f"\n[EDITOR] ✓ Уровень загружен успешно!")
        return processed
    except Exception as e:
        print(f"[EDITOR] ❌ Ошибка обработки: {e}")
        return None


def print_editor_help():
    """Выводит справку по режиму редактирования."""
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    РЕЖИМ РЕДАКТИРОВАНИЯ                      ║
╠══════════════════════════════════════════════════════════════╣
║  Enter    - Перезагрузить уровень из edit_user_level.json    ║
║  R        - Сбросить позицию игрока                          ║
║  Z        - Отменить ход (Undo)                              ║
║  S        - Сохранить состояние                              ║
║  L        - Загрузить состояние                              ║
║  X        - Показать/скрыть требования                       ║
║  F9+F11   - Активировать dev-режим                           ║
╠══════════════════════════════════════════════════════════════╣
║  В консоли (после активации dev):                            ║
║  1 - Показать путь (ans)                                     ║
║  2 - Очистить запись                                         ║
║  3 - Показать координаты                                     ║
║  4 - Показать посещённые клетки                              ║
║  5 - Вкл/выкл победу                                         ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(help_text)
