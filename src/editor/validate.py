def validate_level(level_data):
    """Базовая валидация уровня."""
    errors = []
    warnings = []

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

    if "start" in level_data and "grid" in level_data:
        sx, sy = level_data["start"]
        gx, gy = level_data["grid"]
        if not (0 <= sx < gx and 0 <= sy < gy):
            errors.append(f"start {level_data['start']} вне grid {level_data['grid']}")

    if "movable" in level_data:
        for i, item in enumerate(level_data["movable"]):
            if not isinstance(item, dict):
                errors.append(f"movable[{i}] должен быть объектом")
                continue

            has_pos = any(key in item for key in ["cell", "cells", "range", "ranges"])
            if not has_pos:
                errors.append(f"movable[{i}] не имеет координат (cell/cells/range/ranges)")

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
