from django.urls import path
from . import views

app_name = 'search'
urlpatterns = [
    path('', views.search, name='search'),
    path('palette/', views.palette_search, name='palette'),
]
