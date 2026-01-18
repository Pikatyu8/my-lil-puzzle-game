from src.editor.loader import load_edit_level
from src.editor.validate import validate_level


def reload_edit_level(process_func):
    """
    Перезагружает уровень из файла и обрабатывает его.
    process_func - функция process_level_data из main.py
    """
    print("\n" + "=" * 40)
    print("[EDITOR] Перезагрузка уровня...")
    print("=" * 40)

    data = load_edit_level()
    if data is None:
        return None

    for level in data:
        level.pop("_comment", None)
        level.pop("_examples", None)
        level.pop("_note", None)

    for i, level in enumerate(data):
        print(f"\n[EDITOR] Проверка уровня {i + 1}: {level.get('name', 'Без имени')}")
        if not validate_level(level):
            print("[EDITOR] ❌ Уровень содержит ошибки!")
            return None

    try:
        processed = process_func(data)
        print(f"\n[EDITOR] ✓ Уровень загружен успешно!")
        return processed
    except Exception as e:
        print(f"[EDITOR] ❌ Ошибка обработки: {e}")
        return None
