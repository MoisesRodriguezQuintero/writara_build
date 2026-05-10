from django.urls import path
from . import views

app_name = 'projects'
urlpatterns = [
    path('', views.project_list, name='list'),
    path('new/', views.project_create, name='create'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/delete/', views.project_delete, name='delete'),
    path('<int:pk>/sections/new/', views.section_create, name='section_create'),
    path('<int:pk>/sections/<int:sid>/', views.section_edit, name='section_edit'),
    path('<int:pk>/sections/<int:sid>/save/', views.section_autosave, name='section_save'),
    path('<int:pk>/tasks/<int:tid>/move/', views.task_move, name='task_move'),
]
