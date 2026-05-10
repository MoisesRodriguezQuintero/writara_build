from django.urls import path
from . import views

app_name = 'editor'
urlpatterns = [
    path('', views.document_list, name='list'),
    path('new/', views.document_create, name='create'),
    path('<int:pk>/', views.document_edit, name='edit'),
    path('<int:pk>/delete/', views.document_delete, name='delete'),
    path('<int:pk>/autosave/', views.autosave, name='autosave'),
    path('<int:pk>/favorite/', views.toggle_favorite, name='favorite'),
    path('<int:pk>/versions/<int:vid>/restore/', views.version_restore, name='version_restore'),
    path('<int:pk>/export/<str:fmt>/', views.document_export, name='export'),
    path('<int:pk>/stats/', views.document_stats, name='stats'),
]
