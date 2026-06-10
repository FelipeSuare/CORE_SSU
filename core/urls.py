from django.urls import path
from . import views, api_views

urlpatterns = [
    path('feriados/lista/',                       api_views.FeriadosListView.as_view(),  name='feriados_lista'),
    path('feriados/agregar/',                     api_views.FeriadosCreateView.as_view(), name='feriados_agregar'),
    path('feriados/<int:id_feriado>/editar/',     api_views.FeriadoEditView.as_view(),    name='feriados_editar'),
    path('feriados/<int:id_feriado>/eliminar/',   api_views.FeriadoDeleteView.as_view(),  name='feriados_eliminar'),
]
