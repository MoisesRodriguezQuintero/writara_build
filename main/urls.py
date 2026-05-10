from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/editor/', permanent=False)),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('main.apps.accounts.urls')),
    path('editor/', include('main.apps.editor.urls')),
    path('notes/', include('main.apps.notes.urls')),
    path('projects/', include('main.apps.projects.urls')),
    path('analysis/', include('main.apps.analysis.urls')),
    path('search/', include('main.apps.search.urls')),
]
