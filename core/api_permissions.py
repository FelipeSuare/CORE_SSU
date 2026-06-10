"""
Clases de permisos DRF reutilizables para el sistema SSU.
Reemplazan la lógica manual de verificación de roles en las vistas legacy.
"""

from rest_framework.permissions import BasePermission
from core.roles import obtener_roles


class NoCambioPendiente(BasePermission):
    """Bloquea el acceso si el usuario tiene pendiente un cambio de contraseña forzado."""
    message = 'Debes cambiar tu contraseña inicial antes de continuar.'

    def has_permission(self, request, view):
        if request.session.get('debe_cambiar_contrasena'):
            return False
        return True


class TieneRol(BasePermission):
    """
    Permiso genérico basado en roles. Subclasificar y definir `roles_requeridos`.
    También se puede instanciar directamente: TieneRol.para({'RRHH', 'Administrador'}).
    """
    roles_requeridos: set = set()
    message = 'No tienes el rol necesario para realizar esta acción.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        roles = obtener_roles(request.user.username)
        return bool(roles & self.roles_requeridos)

    @classmethod
    def para(cls, roles: set):
        """Crea una clase de permiso ad-hoc para un conjunto de roles."""
        return type('PermisoDinamico', (cls,), {'roles_requeridos': roles})


# ── Permisos concretos por módulo ─────────────────────────────────────────────

class EsAdminOSistema(TieneRol):
    roles_requeridos = {'Administrador'}


class EsRRHH(TieneRol):
    roles_requeridos = {'RRHH', 'Administrador'}


class EsAprobador(TieneRol):
    roles_requeridos = {
        'Administrador', 'Jefe de Area',
        'Gerente Administrativo', 'Gerente de Salud', 'Gerente General',
    }


class EsAuditoria(TieneRol):
    roles_requeridos = {'Auditoria', 'RRHH', 'Administrador'}


class EsFuncionarioActivo(BasePermission):
    """Cualquier funcionario activo (rol base del sistema)."""
    message = 'Tu cuenta no tiene acceso al sistema.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        roles = obtener_roles(request.user.username)
        return 'Funcionario' in roles
