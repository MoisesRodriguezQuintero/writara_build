from django.urls import path
from . import views

app_name = 'projects'
urlpatterns = [
    path('', views.project_list, name='list'),
    path('new/', views.project_create, name='create'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/delete/', views.project_delete, name='delete'),
    # Sections
    path('<int:pk>/sections/new/', views.section_create, name='section_create'),
    path('<int:pk>/sections/<int:sid>/', views.section_edit, name='section_edit'),
    path('<int:pk>/sections/<int:sid>/save/', views.section_autosave, name='section_save'),
    # Characters
    path('<int:pk>/characters/new/', views.character_create, name='character_create'),
    path('<int:pk>/characters/<int:cid>/delete/', views.character_delete, name='character_delete'),
    # Places
    path('<int:pk>/places/new/', views.place_create, name='place_create'),
    path('<int:pk>/places/<int:pid>/delete/', views.place_delete, name='place_delete'),
    # Tasks
    path('<int:pk>/tasks/new/', views.task_create, name='task_create'),
    path('<int:pk>/tasks/<int:tid>/move/', views.task_move, name='task_move'),
    path('<int:pk>/tasks/<int:tid>/delete/', views.task_delete, name='task_delete'),
]
