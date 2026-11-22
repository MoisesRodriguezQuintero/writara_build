import re

from django.urls import reverse
from django.utils.html import escape
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.text import slugify

WIKI_RE = re.compile(r'\[\[([^\[\]\n]+)\]\]')


# Rutas fijas de /notes/<slug>/: una nota con este slug sería inaccesible
RESERVED_SLUGS = {'new', 'graph', 'quick', 'autocomplete'}


def title_to_slug(title):
    """Mismo criterio para crear el slug de una nota y para resolver [[enlaces]]."""
    slug = slugify(title)[:200] or 'nota'
    return f'{slug}-nota' if slug in RESERVED_SLUGS else slug


def resolve_note(project, title):
    """Nota DEL PROYECTO a la que apunta [[title]] (por título y, si no, por slug).
    Los enlaces solo conectan notas del mismo proyecto."""
    from .models import Note
    title = title.strip()
    if not title:
        return None
    return (Note.objects.filter(project=project, title__iexact=title).first()
            or Note.objects.filter(project=project, slug=title_to_slug(title)).first())


def parse_wiki_links(content, project):
    """Convierte el texto plano de una nota en HTML seguro: escapa todo el texto,
    sustituye [[enlaces]] por <a> y respeta párrafos y saltos de línea."""
    content = (content or '').replace('\r\n', '\n')
    parts, last = [], 0
    for m in WIKI_RE.finditer(content):
        parts.append(escape(content[last:m.start()]))
        title = m.group(1).strip()
        note = resolve_note(project, title)
        if note:
            url = reverse('notes:detail', args=[note.slug])
            parts.append(f'<a class="wiki-link" href="{escape(url)}">{escape(title)}</a>')
        else:
            url = reverse('notes:create') + '?' + urlencode({'title': title, 'project': project.pk})
            parts.append(f'<a class="wiki-link wiki-link--new" href="{escape(url)}">{escape(title)} +</a>')
        last = m.end()
    parts.append(escape(content[last:]))
    text = ''.join(parts).strip()
    if not text:
        return mark_safe('')
    paragraphs = re.split(r'\n{2,}', text)
    return mark_safe(''.join(f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs))


def sync_links(note):
    from .models import NoteLink
    targets = {}
    for m in WIKI_RE.finditer(note.content):
        target = resolve_note(note.project, m.group(1))
        if target and target.pk != note.pk:
            targets[target.pk] = target
    NoteLink.objects.filter(from_note=note).delete()
    NoteLink.objects.bulk_create(
        [NoteLink(from_note=note, to_note=t) for t in targets.values()]
    )


def resync_mentions(project, titles, exclude_pk=None):
    """Re-sincroniza los enlaces de las notas del proyecto que mencionan alguno de `titles`."""
    from .models import Note
    for title in {t.strip() for t in titles if t and t.strip()}:
        others = Note.objects.filter(project=project, content__icontains=title)
        if exclude_pk is not None:
            others = others.exclude(pk=exclude_pk)
        for other in others:
            sync_links(other)


def sync_incoming(note, *titles):
    """Re-sincroniza los enlaces de las notas de su proyecto que mencionan alguno de
    `titles`: así un [[enlace]] escrito antes de que existiera la nota destino (o antes
    de renombrarla) se conecta/desconecta sin tener que volver a guardar la nota origen."""
    resync_mentions(note.project, titles, exclude_pk=note.pk)
