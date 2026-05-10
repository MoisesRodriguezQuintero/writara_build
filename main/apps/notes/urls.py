from django.urls import path
from . import views

app_name = 'notes'
urlpatterns = [
    path('', views.note_list, name='list'),
    path('new/', views.note_create, name='create'),
    path('graph/', views.note_graph, name='graph'),
    path('quick/', views.quick_capture, name='quick_capture'),
    path('autocomplete/', views.note_autocomplete, name='autocomplete'),
    path('<slug:slug>/', views.note_detail, name='detail'),
    path('<slug:slug>/edit/', views.note_edit, name='edit'),
    path('<slug:slug>/save/', views.note_save, name='save'),
    path('<slug:slug>/delete/', views.note_delete, name='delete'),
]
