"""Tamaños de página disponibles (milímetros) y márgenes por defecto.

Se usan en el editor (vista paginada), en la exportación a PDF/HTML (@page) y en
la exportación a ODT (diseño de página)."""

DEFAULT_PAGE_SIZE = 'A5'

PAGE_SIZES = {
    'A3':     {'label': 'A3',            'w': 297,   'h': 420,   'margin': 25},
    'A4':     {'label': 'A4',            'w': 210,   'h': 297,   'margin': 20},
    'A5':     {'label': 'A5',            'w': 148,   'h': 210,   'margin': 18},
    'A6':     {'label': 'A6',            'w': 105,   'h': 148,   'margin': 12},
    'B5':     {'label': 'B5',            'w': 176,   'h': 250,   'margin': 18},
    'LETTER': {'label': 'Carta (Letter)', 'w': 215.9, 'h': 279.4, 'margin': 20},
    'LEGAL':  {'label': 'Legal',         'w': 215.9, 'h': 355.6, 'margin': 20},
}


def mm(value):
    """Número en mm como texto válido para CSS/ODF (siempre con punto decimal,
    aunque la localización de Django use coma)."""
    return f'{value:g}'


def get_page(key):
    """Datos de la página para `key` (si no existe, el tamaño por defecto)."""
    key = key if key in PAGE_SIZES else DEFAULT_PAGE_SIZE
    return {'key': key, **PAGE_SIZES[key]}


PAGE_SIZE_CHOICES = [
    (key, f"{data['label']} ({mm(data['w'])} × {mm(data['h'])} mm)")
    for key, data in PAGE_SIZES.items()
]


def page_options():
    """Lista serializable para el selector del editor."""
    return [
        {'key': key, 'text': text, **PAGE_SIZES[key]}
        for key, text in PAGE_SIZE_CHOICES
    ]
