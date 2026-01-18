import pygame

_font_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        font_names = ["Arial", "Segoe UI", "Tahoma", "DejaVu Sans", "Liberation Sans"]
        font = None
        for name in font_names:
            try:
                font = pygame.font.SysFont(name, size, bold=bold)
                if font.get_height() > 0:
                    break
            except Exception:
                continue
        if font is None:
            font = pygame.font.Font(None, size)
        _font_cache[key] = font
    return _font_cache[key]
