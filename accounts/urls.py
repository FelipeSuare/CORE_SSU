from django.urls import path
from . import views, api_views

urlpatterns = [
    path('', views.login_view, name='login_home'),
    path('perfil/foto/', views.foto_perfil, name='perfil_foto'),
    path('perfil/foto/eliminar/', api_views.EliminarFotoView.as_view(), name='perfil_foto_eliminar'),
    path('api/usuario/mi-perfil/', api_views.MiPerfilView.as_view(), name='mi_perfil_api'),
    path('recuperar/verificar/', api_views.RecuperarVerificarView.as_view(), name='recuperar_verificar'),
    path('recuperar/nueva/', api_views.RecuperarNuevaView.as_view(), name='recuperar_nueva'),
]
