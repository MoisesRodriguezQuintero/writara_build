from django.urls import path
from . import views

app_name = 'analysis'
urlpatterns = [
    path('<int:pk>/', views.document_analysis, name='detail'),
    path('<int:pk>/run/', views.run_analysis, name='run'),
]
