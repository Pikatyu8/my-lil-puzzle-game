import os
import sys

from src.core import config
from src.core.runtime import run_game
from src.data.level_io import load_levels_from_file, process_level_data
from src.editor.help import print_editor_help
from src.editor.reload import reload_edit_level


def main():
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
        print_editor_help()

        config.LEVELS = reload_edit_level(process_level_data)
        if not config.LEVELS:
            print("\n[EDITOR] Создан шаблон. Отредактируйте edit_user_level.json и перезапустите.")
            config.LEVELS = reload_edit_level(process_level_data)

        if config.LEVELS:
            hints = True
            run_game(0, hints, edit_mode_enabled=True)
        else:
            print("[ERROR] Не удалось загрузить уровень для редактирования.")
            sys.exit(1)

    elif mode == "2":
        if os.path.exists("user_levels.json"):
            config.LEVELS = load_levels_from_file("user_levels.json", is_internal=False)
        if not config.LEVELS:
            print("[ERROR] user_levels.json не найден или пуст. Загружаю levels.json...")
            config.LEVELS = load_levels_from_file("levels.json", is_internal=True)

    else:
        config.LEVELS = load_levels_from_file("levels.json", is_internal=True)

    if not edit_mode:
        if not config.LEVELS:
            print("Ошибка: нет уровней.")
            sys.exit(1)

        hints = input("Подсказки? (y): ").strip().lower() in ("да", "yes", "y")

        print(f"\nУровней: {len(config.LEVELS)}")
        for i, lvl in enumerate(config.LEVELS):
            print(f"  {i+1}. {lvl.get('name', f'Уровень {i+1}')}")

        try:
            choice = input(f"\nВыбор (1-{len(config.LEVELS)}): ").strip()
            idx = int(choice) - 1 if choice else 0
            run_game(max(0, min(idx, len(config.LEVELS) - 1)), hints)
        except ValueError:
            run_game(0, hints)


if __name__ == "__main__":
    main()
