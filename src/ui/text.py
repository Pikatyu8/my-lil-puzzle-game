def wrap_text(text, font, max_width):
    """Переносит текст по словам, чтобы он влез в max_width."""
    if font.size(text)[0] <= max_width:
        return [text]

    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word

        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)

            if font.size(word)[0] <= max_width:
                current_line = word
            else:
                chars = list(word)
                current_line = ""
                for char in chars:
                    test = current_line + char
                    if font.size(test)[0] <= max_width:
                        current_line = test
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = char

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]
