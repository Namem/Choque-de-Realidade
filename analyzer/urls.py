from django.urls import path
from . import views

app_name = 'analyzer'
urlpatterns = [
    # A URL da nossa página principal (interface)
    path('', views.index_view, name='index'),
    
    # A nova URL da nossa API de análise
    path('api/analyze/', views.analyze_api_view, name='api_analyze'),
]