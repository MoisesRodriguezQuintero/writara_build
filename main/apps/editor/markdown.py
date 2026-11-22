"""Conversor propio de HTML (el de Quill) a Markdown.

Sustituye a la librería `html2text` (GPL-3.0), para que Writara no dependa de
ningún componente de copyleft fuerte. Cubre las etiquetas que genera el editor:
párrafos, títulos, negrita, cursiva, tachado, código, citas, listas, enlaces,
imágenes y saltos de línea."""
import re
from html.parser import HTMLParser

BLOCKS = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'ul', 'ol', 'li', 'hr'}
VOID = {'br', 'hr', 'img'}
SKIP = {'script', 'style'}


class _Node:
    __slots__ = ('tag', 'attrs', 'children')

    def __init__(self, tag, attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or {}), []


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node('root')
        self.stack = [self.root]
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skipping += 1
            return
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        if tag not in SKIP:
            self.stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skipping = max(0, self.skipping - 1)
            return
        for i in range(len(self.stack) - 1, 0, -1):     # cierra hasta la etiqueta abierta
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if not self.skipping:
            self.stack[-1].children.append(data)


_LINE_START = re.compile(r'^(\s*)(#{1,6}(?=\s)|>|[-+*](?=\s))', re.M)
_ORDERED_START = re.compile(r'^(\s*\d+)([.)])(?=\s)', re.M)


def _escape(text):
    """Escapa lo que Markdown interpretaría como formato."""
    text = re.sub(r'([\\`*_\[\]])', r'\\\1', text)
    text = _LINE_START.sub(lambda m: m.group(1) + '\\' + m.group(2), text)
    return _ORDERED_START.sub(lambda m: m.group(1) + '\\' + m.group(2), text)   # "1\. " (se escapa el punto)


def _wrap(marker, text):
    """Rodea `text` con `marker` dejando los espacios de los extremos fuera
    (Markdown no admite «** hola **»)."""
    core = text.strip()
    if not core:
        return text
    lead = text[:len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    return f'{lead}{marker}{core}{marker}{trail}'


def _inline(node):
    """Contenido en línea de un nodo, ya en Markdown."""
    out = []

    def add(piece):
        # Un espacio al inicio sobra si lo anterior ya acabó en espacio o salto de línea;
        # y un salto duro ("  \n") no debe ir precedido de más espacios.
        if out and out[-1] and piece:
            if out[-1][-1] in ' \n':
                piece = piece.lstrip(' ')
            if piece == '  \n':
                out[-1] = out[-1].rstrip(' ')
        if piece:
            out.append(piece)

    for child in node.children:
        if isinstance(child, str):
            add(_escape(re.sub(r'\s+', ' ', child.replace('\xa0', ' '))))
            continue
        tag = child.tag
        if tag == 'br':
            add('  \n')
        elif tag in ('strong', 'b'):
            add(_wrap('**', _inline(child)))
        elif tag in ('em', 'i'):
            add(_wrap('*', _inline(child)))
        elif tag in ('s', 'strike', 'del'):
            add(_wrap('~~', _inline(child)))
        elif tag == 'code':
            add(_wrap('`', _plain(child)))
        elif tag == 'a':
            text, href = _inline(child).strip(), child.attrs.get('href', '')
            add(f'[{text or href}]({href})' if href else text)
        elif tag == 'img':
            src = child.attrs.get('src', '')
            alt = child.attrs.get('alt', '') or 'imagen'
            add(f'![{alt}]({"(imagen incrustada)" if src.startswith("data:") else src})')
        elif tag in BLOCKS:                                 # bloque dentro de línea: se aplana
            add(' ' + _inline(child).strip() + ' ')
        else:                                               # span, u, sub, sup…
            add(_inline(child))
    return ''.join(out)


def _plain(node):
    """Texto sin formato (para bloques de código)."""
    out = []
    for child in node.children:
        out.append(child if isinstance(child, str) else ('\n' if child.tag == 'br' else _plain(child)))
    return ''.join(out).replace('\xa0', ' ')


def _indent_level(node):
    match = re.search(r'ql-indent-(\d+)', node.attrs.get('class', ''))
    return int(match.group(1)) if match else 0


def _list(node, depth=0):
    lines, number = [], 0
    for item in node.children:
        if isinstance(item, str) or item.tag != 'li':
            continue
        number += 1
        bullet = f'{number}.' if node.tag == 'ol' else '-'
        nested = [c for c in item.children if not isinstance(c, str) and c.tag in ('ul', 'ol')]
        own = _Node('li')
        own.children = [c for c in item.children if c not in nested]
        indent = '    ' * (depth + _indent_level(item))
        text = _inline(own).strip().replace('  \n', '\n' + indent + '  ')
        lines.append(f'{indent}{bullet} {text}')
        for sub in nested:
            lines.append(_list(sub, depth + 1))
    return '\n'.join(lines)


def _blocks(node):
    out = []
    loose = _Node('p')                    # texto/inline suelto entre bloques

    def flush():
        text = _inline(loose).strip()
        if text:
            out.append(text)
        loose.children = []

    for child in node.children:
        if isinstance(child, str) or child.tag not in BLOCKS:
            loose.children.append(child)
            continue
        flush()
        tag = child.tag
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            text = _inline(child).strip()
            if text:
                out.append('#' * int(tag[1]) + ' ' + text)
        elif tag in ('p', 'div'):
            if any(not isinstance(c, str) and c.tag in BLOCKS for c in child.children):
                out.extend(_blocks(child))
            else:
                text = _inline(child).strip()
                if text:
                    out.append(text)
        elif tag == 'blockquote':
            text = _inline(child).strip()
            if text:
                out.append('\n'.join('> ' + line for line in text.split('\n')))
        elif tag == 'pre':
            code = _plain(child).strip('\n')
            if code.strip():
                out.append('```\n' + code + '\n```')
        elif tag in ('ul', 'ol'):
            text = _list(child)
            if text:
                out.append(text)
        elif tag == 'li':                                   # <li> suelto
            out.append('- ' + _inline(child).strip())
        elif tag == 'hr':
            out.append('---')
    flush()
    return out


def html_to_markdown(html):
    """HTML → Markdown. Devuelve texto terminado en un salto de línea."""
    builder = _TreeBuilder()
    builder.feed(html or '')
    builder.close()
    text = '\n\n'.join(_blocks(builder.root))
    return text + '\n' if text else ''
