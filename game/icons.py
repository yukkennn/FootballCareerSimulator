"""Иконки интерфейса, нарисованные для игры (вместо эмодзи на кнопках): SVG 24x24, линии цветом текста.

svg(name)        - строка <svg> для сайта (цвет - currentColor, размер задаёт CSS: .ic)
qicon(name, c)   - QIcon для версии для компьютера (цвет c), импортирует PySide6 только при вызове
"""

# содержимое <svg viewBox="0 0 24 24">: stroke - currentColor, fill - none (кроме помеченных fill="currentColor")
ICONS = {
    # мяч: круг, пятиугольник в центре и швы к краю
    "ball": ('<circle cx="12" cy="12" r="9"/><path d="M12 8.6L15.23 10.95L14 14.75L10 14.75L8.77 10.95Z" fill="currentColor"/>'
            '<path d="M12 8.6V5.7M15.23 10.95l2.76-.9M14 14.75l1.7 2.35M10 14.75l-1.7 2.35M8.77 10.95l-2.76-.9" stroke-width="1.5"/>'
            '<path d="M12 5.7L9.37 3.39A9 9 0 0 1 14.63 3.39ZM17.99 10.05L19.37 6.84A9 9 0 0 1 21 11.84ZM15.7 17.1L19.19 17.42'
            'A9 9 0 0 1 14.93 20.51ZM8.3 17.1L9.07 20.51A9 9 0 0 1 4.81 17.42ZM6.01 10.05L3 11.84A9 9 0 0 1 4.63 6.84Z" '
            'fill="currentColor" stroke="none"/>'),
    "board": ('<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2.5" width="6" height="3" rx="1" fill="currentColor"/>'
             '<circle cx="9" cy="11" r="1.5" fill="currentColor"/><circle cx="15" cy="11" r="1.5" fill="currentColor"/>'
             '<circle cx="12" cy="16.5" r="1.5" fill="currentColor"/>'),
    "play": '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
    # дневник: раскрытая книга
    "book": '<path d="M12 6.5C10 5 7 4.5 3.5 5v13c3.5-.5 6.5 0 8.5 1.5 2-1.5 5-2 8.5-1.5V5C17 4.5 14 5 12 6.5z"/><path d="M12 6.5v13"/>',
    # настройки: шестерёнка
    "gear": ('<circle cx="12" cy="12" r="3.2"/><path d="M19.45 10.49L22.11 10.68L22.11 13.32L19.45 13.51L18.33 16.2L20.09 18.22'
            'L18.22 20.09L16.2 18.33L13.51 19.45L13.32 22.11L10.68 22.11L10.49 19.45L7.8 18.33L5.78 20.09L3.91 18.22L5.67 16.2'
            'L4.55 13.51L1.89 13.32L1.89 10.68L4.55 10.49L5.67 7.8L3.91 5.78L5.78 3.91L7.8 5.67L10.49 4.55L10.68 1.89L13.32 1.89'
            'L13.51 4.55L16.2 5.67L18.22 3.91L20.09 5.78L18.33 7.8Z" stroke-width="1.6"/>'),
    "dice": '<rect x="4" y="4" width="16" height="16" rx="3.5"/><circle cx="8.5" cy="8.5" r="1.4" fill="currentColor"/>'
            '<circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="15.5" cy="15.5" r="1.4" fill="currentColor"/>',
    # меню: три полосы
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    # сборная: флажок на древке
    "flag": '<path d="M6 21V4"/><path d="M6 4.5h11l-2.5 4 2.5 4H6" fill="currentColor"/>',
}

def svg(name, extra_class=""):
    """Иконка для HTML: размер и отступ задаёт CSS (класс ic), цвет - цвет текста кнопки."""
    cls = "ic" + (" " + extra_class if extra_class else "")
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')

_qcache = {}

def _pixmap(name, color, size):
    from PySide6.QtGui import QPixmap
    data = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            + ICONS[name].replace("currentColor", color) + "</svg>")
    pm = QPixmap()
    pm.loadFromData(data.encode("utf-8"), "SVG")
    return pm

def qicon(name, color, color_on=None, size=48):
    """QIcon для кнопок версии для компьютера (рисуется из того же SVG нужным цветом); color_on - цвет у нажатой
    (выбранной) кнопки-переключателя."""
    key = (name, color, color_on, size)
    if key not in _qcache:
        from PySide6.QtGui import QIcon
        ic = QIcon()
        ic.addPixmap(_pixmap(name, color, size), QIcon.Normal, QIcon.Off)
        if color_on:
            ic.addPixmap(_pixmap(name, color_on, size), QIcon.Normal, QIcon.On)
        _qcache[key] = ic
    return _qcache[key]
