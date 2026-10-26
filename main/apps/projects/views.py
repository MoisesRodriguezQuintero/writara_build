from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Project, Section, Character, Place, Task, TimelineEvent
from main.apps.accounts.models import UserPreferences
from main.utils import clean_html, count_words, json_body, short_text, valid_color

TASK_STATUSES = {value for value, _ in Task.STATUS_CHOICES}
CHARACTER_ROLES = {value for value, _ in Character.ROLE_CHOICES}


def _id_list(value):
    """Lista de ids enteros a partir de un valor JSON arbitrario."""
    if not isinstance(value, list):
        return []
    return [i for i in value if isinstance(i, int) and not isinstance(i, bool)]


def get_prefs(user):
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    return prefs

@login_required
def project_list(request):
    projects = Project.objects.filter(owner=request.user)
    prefs = get_prefs(request.user)
    return render(request, 'projects/list.html', {'projects': projects, 'prefs': prefs, 'active': 'projects'})

@login_required
def project_create(request):
    if request.method == 'POST':
        p = Project.objects.create(
            owner=request.user,
            name=short_text(request.POST.get('name'), 'Nuevo proyecto'),
            description=request.POST.get('description', ''),
            cover_color=valid_color(request.POST.get('cover_color')),
        )
        return redirect('projects:detail', p.pk)
    prefs = get_prefs(request.user)
    return render(request, 'projects/create.html', {'prefs': prefs, 'active': 'projects'})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    sections = project.sections.all()
    characters = project.characters.all()
    places = project.places.all()
    tasks = project.tasks.all()
    prefs = get_prefs(request.user)
    total_words = sum(s.word_count for s in sections)
    events = project.events.all().prefetch_related('characters', 'places')
    return render(request, 'projects/detail.html', {
        'project': project, 'sections': sections, 'characters': characters,
        'places': places, 'tasks': tasks, 'total_words': total_words,
        'prefs': prefs, 'active': 'projects',
        'events': events,
    })

@login_required
def section_edit(request, pk, sid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    section = get_object_or_404(Section, pk=sid, project=project)
    prefs = get_prefs(request.user)
    return render(request, 'projects/section_editor.html', {
        'project': project, 'section': section, 'prefs': prefs
    })

@login_required
@require_POST
def section_autosave(request, pk, sid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    section = get_object_or_404(Section, pk=sid, project=project)
    data = json_body(request)
    section.title = short_text(data.get('title', section.title), 'Sin título')
    content = data.get('content', section.content)
    if isinstance(content, str):
        section.content = clean_html(content)
    section.word_count = count_words(section.content)
    section.save()
    return JsonResponse({'saved_at': section.updated_at.strftime('%H:%M:%S'), 'word_count': section.word_count})

@login_required
@require_POST
def section_create(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json_body(request)
    order = project.sections.count()
    s = Section.objects.create(project=project, title=short_text(data.get('title'), 'Nueva sección'), order=order)
    return JsonResponse({'id': s.pk, 'title': s.title})

@login_required
@require_POST
def task_move(request, pk, tid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    task = get_object_or_404(Task, pk=tid, project=project)
    data = json_body(request)
    status = data.get('status', task.status)
    if status not in TASK_STATUSES:
        return JsonResponse({'error': 'Estado no válido'}, status=400)
    task.status = status
    task.save()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.delete()
    return redirect('projects:list')

@login_required
@require_POST
def character_create(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json_body(request)
    c = Character.objects.create(
        project=project,
        name=short_text(data.get('name'), 'Personaje'),
        role=data.get('role') if data.get('role') in CHARACTER_ROLES else 'secondary',
        description=str(data.get('description', '')),
    )
    return JsonResponse({'id': c.pk, 'name': c.name, 'role': c.role, 'role_display': c.get_role_display(), 'description': c.description})

@login_required
@require_POST
def character_delete(request, pk, cid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    char = get_object_or_404(Character, pk=cid, project=project)
    char.delete()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def place_create(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json_body(request)
    p = Place.objects.create(
        project=project,
        name=short_text(data.get('name'), 'Lugar'),
        description=str(data.get('description', '')),
    )
    return JsonResponse({'id': p.pk, 'name': p.name, 'description': p.description})

@login_required
@require_POST
def place_delete(request, pk, pid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    place = get_object_or_404(Place, pk=pid, project=project)
    place.delete()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def task_create(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json_body(request)
    order = project.tasks.count()
    status = data.get('status', 'todo')
    t = Task.objects.create(
        project=project,
        title=short_text(data.get('title'), 'Nueva tarea'),
        status=status if status in TASK_STATUSES else 'todo',
        order=order,
    )
    return JsonResponse({'id': t.pk, 'title': t.title, 'status': t.status})

@login_required
@require_POST
def task_delete(request, pk, tid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    task = get_object_or_404(Task, pk=tid, project=project)
    task.delete()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def event_create(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json_body(request)
    order = project.events.count()
    event = TimelineEvent.objects.create(
        project=project,
        title=short_text(data.get('title'), 'Nuevo evento'),
        description=str(data.get('description', '')),
        date_label=short_text(data.get('date_label'), '', 100),
        order=order,
    )
    char_ids = _id_list(data.get('character_ids', []))
    place_ids = _id_list(data.get('place_ids', []))
    if char_ids:
        event.characters.set(Character.objects.filter(pk__in=char_ids, project=project))
    if place_ids:
        event.places.set(Place.objects.filter(pk__in=place_ids, project=project))
    return JsonResponse({
        'id': event.pk,
        'title': event.title,
        'description': event.description,
        'date_label': event.date_label,
        'order': event.order,
        'characters': [{'id': c.pk, 'name': c.name} for c in event.characters.all()],
        'places': [{'id': p.pk, 'name': p.name} for p in event.places.all()],
    })

@login_required
@require_POST
def event_update(request, pk, eid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    event = get_object_or_404(TimelineEvent, pk=eid, project=project)
    data = json_body(request)
    event.title = short_text(data.get('title', event.title), event.title)
    event.description = str(data.get('description', event.description))
    event.date_label = short_text(data.get('date_label', event.date_label), '', 100)
    event.save()
    char_ids = _id_list(data.get('character_ids', []))
    place_ids = _id_list(data.get('place_ids', []))
    event.characters.set(Character.objects.filter(pk__in=char_ids, project=project))
    event.places.set(Place.objects.filter(pk__in=place_ids, project=project))
    return JsonResponse({'ok': True})

@login_required
@require_POST
def event_reorder(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json_body(request)
    for item in data.get('order', []):
        if isinstance(item, dict) and isinstance(item.get('id'), int) and isinstance(item.get('order'), int):
            TimelineEvent.objects.filter(pk=item['id'], project=project).update(order=item['order'])
    return JsonResponse({'ok': True})

@login_required
@require_POST
def event_delete(request, pk, eid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    event = get_object_or_404(TimelineEvent, pk=eid, project=project)
    event.delete()
    return JsonResponse({'ok': True})