from django import template
from django.utils.safestring import mark_safe

from main.utils import clean_html

register = template.Library()


@register.filter(name='safe_html')
def safe_html(value):
    """HTML saneado y marcado como seguro (para renderizar contenido de usuario)."""
    return mark_safe(clean_html(value))


@register.filter(name='clean_html')
def clean_html_filter(value):
    """HTML saneado pero SIN marcar como seguro (se escapa al volcarlo en plantilla)."""
    return clean_html(value)
