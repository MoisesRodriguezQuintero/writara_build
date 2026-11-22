from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from main.apps.accounts.models import UserPreferences
from main.apps.projects.models import Project, general_project_for
from main.utils import json_body, short_text
from .models import Note, Tag, NoteLink
from .utils import parse_wiki_links, resolve_note, resync_mentions, sync_incoming, sync_links


def get_prefs(user):
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    return prefs


def _project_from_request(user, raw):
    """Proyecto del usuario con ese id, o None si no es válido o no es suyo."""
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        return None
    return Project.objects.filter(owner=user, pk=pk).first()


def _project_notes_url(project):
    return reverse('projects:detail', args=[project.pk]) + '#notes'


@login_required
def note_list(request):
    """Búsqueda y filtros de notas (de todos los proyectos o de uno: ?project=<id>).
    El día a día de las notas está en la pestaña «Notas» de cada proyecto."""
    project = _project_from_request(request.user, request.GET.get('project'))
    notes = (Note.objects.filter(owner=request.user, is_inbox=False)
             .select_related('project').prefetch_related('tags'))
    inbox = Note.objects.filter(owner=request.user, is_inbox=True).select_related('project')
    tags = Tag.objects.filter(owner=request.user, notes__owner=request.user)
    if project:
        notes, inbox = notes.filter(project=project), inbox.filter(project=project)
        tags = tags.filter(notes__project=project)
    tag_filter = request.GET.get('tag')
    search_q = request.GET.get('q', '')
    if tag_filter:
        notes = notes.filter(tags__name=tag_filter)
    if search_q:
        notes = notes.filter(Q(title__icontains=search_q) | Q(content__icontains=search_q))
    return render(request, 'notes/list.html', {
        'notes': notes, 'tags': tags.distinct(), 'tag_filter': tag_filter,
        'search_q': search_q, 'inbox': inbox, 'project': project,
        'prefs': get_prefs(request.user), 'active': 'projects',
    })


@login_required
def note_detail(request, slug):
    note = get_object_or_404(Note.objects.select_related('project'), slug=slug, owner=request.user)
    backlinks = NoteLink.objects.filter(to_note=note).select_related('from_note')
    outgoing = NoteLink.objects.filter(from_note=note).select_related('to_note')
    return render(request, 'notes/detail.html', {
        'note': note, 'project': note.project,
        'content': parse_wiki_links(note.content, note.project),
        'backlinks': backlinks, 'outgoing': outgoing,
        'prefs': get_prefs(request.user), 'active': 'projects',
    })


@login_required
def note_create(request):
    """Crea una nota en el proyecto indicado (?project=<id>) o en «Notas generales»."""
    project = (_project_from_request(request.user, request.GET.get('project'))
               or general_project_for(request.user))
    raw_title = (request.GET.get('title') or '').strip()
    title = short_text(raw_title, 'Nueva nota')
    if raw_title:
        # Venimos de un [[enlace]] a una nota nueva: si ya existe, no se duplica
        existing = resolve_note(project, title)
        if existing:
            return redirect('notes:edit', existing.slug)
    note = Note.objects.create(owner=request.user, project=project, title=title)
    if raw_title:
        sync_incoming(note, title)
    return redirect('notes:edit', note.slug)


@login_required
def note_edit(request, slug):
    note = get_object_or_404(Note.objects.select_related('project'), slug=slug, owner=request.user)
    return render(request, 'notes/edit.html', {
        'note': note, 'project': note.project,
        'projects': Project.objects.filter(owner=request.user).order_by('-is_general', 'name'),
        'tags': Tag.objects.filter(owner=request.user),
        'note_tags': [t.name for t in note.tags.all()],
        'prefs': get_prefs(request.user), 'active': 'projects',
    })


@login_required
@require_POST
def note_save(request, slug):
    note = get_object_or_404(Note.objects.select_related('project'), slug=slug, owner=request.user)
    data = json_body(request)
    old_title, old_project = note.title, note.project
    note.title = short_text(data.get('title', note.title), 'Sin título')
    content = data.get('content', note.content)
    note.content = content if isinstance(content, str) else note.content
    # Mover la nota a otro proyecto (solo a uno propio)
    target = _project_from_request(request.user, data.get('project')) if 'project' in data else None
    moved = target is not None and target.pk != old_project.pk
    if moved:
        note.project = target
    # Etiquetas: por usuario, sin vacíos ni duplicados, con límite de longitud
    raw_tags = data.get('tags', [])
    tag_names = []
    for name in raw_tags if isinstance(raw_tags, list) else []:
        name = str(name).strip()[:50]
        if name and name not in tag_names:
            tag_names.append(name)
    note.is_inbox = False   # una nota de inbox editada ya está procesada
    note.save()
    note.tags.set([Tag.objects.get_or_create(owner=request.user, name=n)[0] for n in tag_names[:30]])
    if moved:
        # Los enlaces solo existen dentro de un proyecto: se cortan los que venían del antiguo
        NoteLink.objects.filter(to_note=note).exclude(from_note__project=note.project).delete()
        resync_mentions(old_project, [old_title, note.title], exclude_pk=note.pk)
    sync_links(note)
    if moved or note.title != old_title:
        sync_incoming(note, old_title, note.title)
    return JsonResponse({
        'saved_at': note.updated_at.strftime('%H:%M:%S'), 'slug': note.slug,
        'project': {'id': note.project_id, 'name': note.project.name,
                    'url': _project_notes_url(note.project)},
    })


@login_required
@require_POST
def note_delete(request, slug):
    note = get_object_or_404(Note.objects.select_related('project'), slug=slug, owner=request.user)
    project = note.project
    note.delete()
    return redirect(_project_notes_url(project))


@login_required
def note_graph(request):
    """Grafo de enlaces entre notas: de un proyecto (?project=<id>) o de todos."""
    project = _project_from_request(request.user, request.GET.get('project'))
    notes = Note.objects.filter(owner=request.user, is_inbox=False)
    links = NoteLink.objects.filter(from_note__owner=request.user)
    if project:
        notes = notes.filter(project=project)
        links = links.filter(from_note__project=project)
    nodes = [{'id': n.pk, 'label': n.title, 'slug': n.slug} for n in notes]
    ids = {n['id'] for n in nodes}
    # d3 falla si una arista apunta a un nodo que no está (p. ej. una nota de inbox)
    edges = [{'source': l.from_note_id, 'target': l.to_note_id} for l in links
             if l.from_note_id in ids and l.to_note_id in ids]
    return render(request, 'notes/graph.html', {
        'nodes': nodes, 'edges': edges, 'project': project,
        'prefs': get_prefs(request.user), 'active': 'projects',
    })


@login_required
@require_POST
def quick_capture(request):
    """Captura rápida: va a la bandeja del proyecto en el que estás (project_id) o,
    si no hay ninguno, a «Notas generales»."""
    data = json_body(request)
    content = str(data.get('content', '')).strip()
    project = (_project_from_request(request.user, data.get('project_id'))
               or general_project_for(request.user))
    if content:
        title = content[:50] + ('...' if len(content) > 50 else '')
        Note.objects.create(owner=request.user, project=project, title=title,
                            content=content, is_inbox=True)
    return JsonResponse({'ok': True, 'project': project.name})


@login_required
def note_autocomplete(request):
    q = request.GET.get('q', '')
    notes = Note.objects.filter(owner=request.user, title__icontains=q)
    project = _project_from_request(request.user, request.GET.get('project'))
    if project:
        notes = notes.filter(project=project)
    return JsonResponse({'results': [{'title': n.title, 'slug': n.slug} for n in notes[:8]]})
