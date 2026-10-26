from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.http import content_disposition_header

from main.apps.accounts.models import UserPreferences
from main.utils import clean_html, json_body, short_text
from .exporters import DocumentExporter
from .models import Document, DocumentVersion

SNAPSHOT_EVERY = timedelta(minutes=30)

# formato → (extensión, content-type)
EXPORT_FORMATS = {
    'markdown': ('md', 'text/markdown'),
    'html': ('html', 'text/html'),
    'txt': ('txt', 'text/plain'),
    'odt': ('odt', 'application/vnd.oasis.opendocument.text'),
    'pdf': ('pdf', 'application/pdf'),
}


def get_prefs(user):
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    return prefs

@login_required
def document_list(request):
    docs = Document.objects.filter(owner=request.user, is_archived=False)
    recent = docs.order_by('-updated_at')[:20]
    favorites = docs.filter(is_favorite=True)
    prefs = get_prefs(request.user)
    return render(request, 'editor/list.html', {
        'docs': recent, 'favorites': favorites, 'prefs': prefs,
        'active': 'editor'
    })

@login_required
def document_create(request):
    doc = Document.objects.create(owner=request.user, title='Sin título')
    return redirect('editor:edit', doc.pk)

@login_required
def document_edit(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    prefs = get_prefs(request.user)
    versions = doc.versions.all()[:10]
    return render(request, 'editor/editor.html', {
        'doc': doc, 'prefs': prefs, 'versions': versions,
        'word_count': doc.word_count(),
    })

@login_required
@require_POST
def autosave(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    data = json_body(request)
    doc.title = short_text(data.get('title', doc.title), 'Sin título')
    if 'content' in data:
        if not isinstance(data['content'], str):
            return JsonResponse({'error': 'content debe ser texto'}, status=400)
        doc.content = clean_html(data['content'])
    doc.save()
    # Instantánea de versión: la primera con contenido y después como mucho una
    # cada 30 minutos, y solo si el contenido cambió.
    last = doc.versions.first()
    if last is None:
        should_snapshot = bool(doc.content.strip())
    else:
        should_snapshot = (timezone.now() - last.created_at > SNAPSHOT_EVERY
                           and last.content != doc.content)
    if should_snapshot:
        DocumentVersion.objects.create(
            document=doc, content=doc.content, word_count=doc.word_count()
        )
    return JsonResponse({
        'saved_at': timezone.localtime(doc.updated_at).strftime('%H:%M:%S'),
        'word_count': doc.word_count(),
    })

@login_required
@require_POST
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    doc.delete()
    return redirect('editor:list')

@login_required
@require_POST
def toggle_favorite(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    doc.is_favorite = not doc.is_favorite
    doc.save()
    return JsonResponse({'is_favorite': doc.is_favorite})

@login_required
@require_POST
def version_restore(request, pk, vid):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    version = get_object_or_404(DocumentVersion, pk=vid, document=doc)
    if doc.content != version.content:
        # Guardar el estado actual para que restaurar se pueda deshacer
        DocumentVersion.objects.create(
            document=doc, content=doc.content, word_count=doc.word_count()
        )
    doc.content = clean_html(version.content)
    doc.save()
    return redirect('editor:edit', pk)

@login_required
def document_export(request, pk, fmt):
    if fmt not in EXPORT_FORMATS:
        raise Http404('Formato de exportación desconocido')
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    exp = DocumentExporter(doc)
    builders = {
        'markdown': exp.to_markdown,
        'html': exp.to_html,
        'txt': exp.to_text,
        'odt': exp.to_odt,
        'pdf': exp.to_pdf,
    }
    extension, content_type = EXPORT_FORMATS[fmt]
    response = HttpResponse(builders[fmt](), content_type=content_type)
    response['Content-Disposition'] = content_disposition_header(
        True, f'{doc.title or "documento"}.{extension}'
    )
    return response

@login_required
def document_stats(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    from main.apps.analysis.engine import analyze
    stats = analyze(doc.content)
    return JsonResponse(stats)
