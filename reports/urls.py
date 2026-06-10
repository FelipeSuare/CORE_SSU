from django.urls import path
from . import views, api_views

urlpatterns = [
    path('api/reportes/personal/unidades/',     api_views.UnidadesReporteView.as_view(),      name='rp_unidades'),
    path('api/reportes/personal/funcionarios/', api_views.FuncionariosReporteView.as_view(),   name='rp_funcionarios'),
    path('api/reportes/personal/historial/',    api_views.HistorialReporteView.as_view(),      name='rp_historial'),
]
