import logging
from django.shortcuts import render
from django.urls import resolve, Resolver404

logger = logging.getLogger('ssu.acceso_denegado')


def _obtener_roles(request) -> set:
    """Obtiene los roles del usuario y los cachea en request._ssu_roles."""
    if hasattr(request, '_ssu_roles'):
        return request._ssu_roles

    from employees.models import Funcionario
    from accounts.models import FuncionarioRol
    try:
        f = Funcionario.objects.get(ci__ci=request.user.username, estado='ACTIVO')
        roles = set(
            FuncionarioRol.objects
            .filter(cod_funcionario=f, activo=True)
            .values_list('id_roles__tipo_rol', flat=True)
        )
    except Exception:
        roles = set()

    roles.add('Funcionario')
    request._ssu_roles = roles
    return roles


class ControlAccesoRoles:
    """
    Verifica permisos de rol antes de despachar cada vista HTML.
    - Bloquea el acceso si el usuario no tiene el rol requerido.
    - Registra el intento en log y en la tabla intentos_acceso.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self._verificar(request)
        if respuesta:
            return respuesta
        return self.get_response(request)

    def _verificar(self, request):
        if not request.user.is_authenticated:
            return None

        try:
            url_name = resolve(request.path_info).url_name
        except Resolver404:
            return None

        if not url_name:
            return None

        from core.permissions import puede_acceder
        roles = _obtener_roles(request)

        if not puede_acceder(roles, url_name):
            self._registrar(request, url_name, roles)
            return render(request, 'shared/sin_acceso.html', status=403)

        return None

    @staticmethod
    def _registrar(request, url_name: str, roles: set):
        logger.warning(
            'ACCESO_DENEGADO | usuario=%s | path=%s | url_name=%s | roles=%s | ip=%s',
            request.user.username,
            request.path,
            url_name,
            ','.join(sorted(roles)),
            request.META.get('REMOTE_ADDR', '—'),
        )
        try:
            from core.models import IntentosAcceso
            IntentosAcceso.objects.create(
                username=request.user.username,
                path=request.path,
                url_name=url_name,
                roles=','.join(sorted(roles)),
                ip=request.META.get('REMOTE_ADDR') or None,
            )
        except Exception:
            pass  # El log de archivo es suficiente si falla la BD
