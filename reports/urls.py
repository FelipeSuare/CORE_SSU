from django.urls import path
from . import views

urlpatterns = [
    path('api/reportes/personal/unidades/',     views.api_rp_unidades,     name='rp_unidades'),
    path('api/reportes/personal/funcionarios/', views.api_rp_funcionarios,  name='rp_funcionarios'),
    path('api/reportes/personal/historial/',    views.api_rp_historial,     name='rp_historial'),
]
