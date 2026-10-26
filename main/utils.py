"""Utilidades compartidas: saneado de HTML, texto plano, JSON y validaciones."""
import html
import json
import re

import bleach
from django.core.exceptions import BadRequest

# ── Saneado de HTML (contenido de Quill) ─────────────────────────────────────
ALLOWED_TAGS = frozenset([
    'p', 'br', 'hr', 'div', 'span',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del', 'sub', 'sup',
    'blockquote', 'pre', 'code', 'ol', 'ul', 'li', 'a', 'img',
])

_SAFE_HREF = re.compile(r'^(?:https?://|mailto:|/|#)', re.I)
_SAFE_IMG = re.compile(
    r'^(?:https?://|data:image/(?:png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=\s]+$)', re.I
)
_CLASS_OK = re.compile(r'^[\w\- ]*$')


def _attr_allowed(tag, name, value):
    if name == 'class':
        return bool(_CLASS_OK.match(value))
    if tag == 'a':
        if name == 'href':
            return bool(_SAFE_HREF.match(value.strip()))
        return name in ('title', 'target', 'rel')
    if tag == 'img':
        if name == 'src':
            return bool(_SAFE_IMG.match(value.strip()))
        return name in ('alt', 'title', 'width', 'height')
    if tag == 'pre':
        return name == 'spellcheck'
    return False


def clean_html(value):
    """Elimina scripts, manejadores de eventos y URLs peligrosas del HTML."""
    if not value:
        return ''
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=_attr_allowed,
        protocols=['http', 'https', 'mailto', 'data'],
        strip=True,
        strip_comments=True,
    )


# ── HTML → texto ──────────────────────────────────────────────────────────────
_BLOCK_END_RE = re.compile(r'</(?:p|h[1-6]|li|blockquote|pre|div|ul|ol)\s*>', re.I)
_BR_RE = re.compile(r'<br\s*/?>', re.I)
_TAG_RE = re.compile(r'<[^>]*>')


def html_to_text(value, keep_breaks=True):
    """Convierte HTML de Quill en texto. Los bloques acaban en salto de línea;
    las etiquetas en línea (<strong>, <em>…) se eliminan sin añadir espacios para
    no partir palabras, y las entidades (&nbsp;, &amp;…) se decodifican."""
    if not value:
        return ''
    text = _BR_RE.sub('\n' if keep_breaks else ' ', value)
    text = _BLOCK_END_RE.sub('\n', text)
    text = _TAG_RE.sub('', text)
    return html.unescape(text).replace('\xa0', ' ')


def count_words(value):
    return len(html_to_text(value).split())


# ── Peticiones JSON y validaciones ───────────────────────────────────────────
def json_body(request):
    """Devuelve el cuerpo JSON como dict o provoca un 400 (en vez de un 500)."""
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        raise BadRequest('JSON inválido')
    if not isinstance(data, dict):
        raise BadRequest('Se esperaba un objeto JSON')
    return data


def to_int(value, default, lo, hi):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, number))


_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')


def valid_color(value, default='#6366f1'):
    return value if isinstance(value, str) and _COLOR_RE.match(value) else default


def short_text(value, default, max_length=255):
    """Cadena recortada al límite del campo; usa `default` si queda vacía."""
    text = str(value if value is not None else '').strip()
    return text[:max_length] if text else default
