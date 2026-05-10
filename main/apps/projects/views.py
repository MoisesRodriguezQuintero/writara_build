import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Project, Section, Character, Place, Task
from main.apps.accounts.models import UserPreferences

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
            name=request.POST.get('name', 'Nuevo proyecto'),
            description=request.POST.get('description', ''),
            cover_color=request.POST.get('cover_color', '#6366f1'),
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
    return render(request, 'projects/detail.html', {
        'project': project, 'sections': sections, 'characters': characters,
        'places': places, 'tasks': tasks, 'total_words': total_words,
        'prefs': prefs, 'active': 'projects',
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
    data = json.loads(request.body)
    import re
    section.title = data.get('title', section.title) or 'Sin título'
    section.content = data.get('content', section.content)
    text = re.sub(r'<[^>]+>', ' ', section.content)
    section.word_count = len(text.split())
    section.save()
    return JsonResponse({'saved_at': section.updated_at.strftime('%H:%M:%S'), 'word_count': section.word_count})

@login_required
@require_POST
def section_create(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    data = json.loads(request.body)
    order = project.sections.count()
    s = Section.objects.create(project=project, title=data.get('title', 'Nueva sección'), order=order)
    return JsonResponse({'id': s.pk, 'title': s.title})

@login_required
@require_POST
def task_move(request, pk, tid):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    task = get_object_or_404(Task, pk=tid, project=project)
    data = json.loads(request.body)
    task.status = data.get('status', task.status)
    task.save()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.delete()
    return redirect('projects:list')
