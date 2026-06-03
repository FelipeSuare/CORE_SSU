from django.urls import path
from . import views

urlpatterns = [
    # Solicitud de Vacaciones
    path('api/vacaciones/datos/',            views.datos_formulario,       name='vac_datos'),
    path('api/vacaciones/calcular-retorno/', views.calcular_retorno_api,   name='vac_calcular_retorno'),
    path('api/vacaciones/crear/',            views.crear_solicitud,         name='vac_crear'),
    path('api/vacaciones/mis-solicitudes/',  views.mis_solicitudes,         name='vac_mis_solicitudes'),
    path('api/vacaciones/seguimiento/',      views.seguimiento_solicitud,   name='vac_seguimiento'),
    # Aprobación y/o Rechazo
    path('api/vacaciones/para-aprobar/',     views.solicitudes_para_aprobar, name='vac_para_aprobar'),
    path('api/vacaciones/decision/',         views.registrar_decision,       name='vac_decision'),
    # Historial RRHH
    path('api/vacaciones/historial-rrhh/',                           views.api_historial_rrhh,  name='vac_historial_rrhh'),
    path('api/vacaciones/historial-rrhh/pdf/<int:id_formulario>/',   views.api_descargar_pdf,   name='vac_pdf'),
    # Gestión de saldo (RRHH)
    path('api/vacaciones/acreditar-gestion/',                        views.acreditar_gestion,    name='vac_acreditar_gestion'),
    path('api/vacaciones/inicializar/',                              views.inicializar_vacaciones, name='vac_inicializar'),
    # Anulación y ajuste (RRHH)
    path('api/vacaciones/anulacion/',            views.api_solicitudes_anulacion, name='vac_anulacion_list'),
    path('api/vacaciones/anulacion/registrar/',  views.api_registrar_anulacion,   name='vac_anulacion_registrar'),
]
