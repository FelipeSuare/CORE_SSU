from employees.models import Persona


def foto_perfil(request):
    if not request.user.is_authenticated:
        return {'tiene_foto_perfil': False}
    try:
        persona = Persona.objects.only('foto').get(ci=request.user.username)
        return {'tiene_foto_perfil': bool(persona.foto)}
    except Persona.DoesNotExist:
        return {'tiene_foto_perfil': False}


def permisos_usuario(request):
    """
    Inyecta en cada template:
      modulos_permitidos — set de url_names accesibles por el usuario actual
      roles_activos      — lista de roles del usuario (sin 'Funcionario' si tiene otros)
      rol_principal      — rol más representativo para mostrar en UI
    """
    if not request.user.is_authenticated:
        return {
            'modulos_permitidos': frozenset(),
            'roles_activos':      [],
            'rol_principal':      '',
        }

    from core.middleware import _obtener_roles
    from core.permissions import PERMISOS, URL_ABIERTAS, PRIORIDAD_ROL

    roles = _obtener_roles(request)

    modulos_permitidos = URL_ABIERTAS | {
        nombre
        for nombre, permitidos in PERMISOS.items()
        if roles & permitidos
    }

    rol_principal = next((r for r in PRIORIDAD_ROL if r in roles), 'Funcionario')

    roles_display = sorted(roles - {'Funcionario'}) if len(roles) > 1 else ['Funcionario']

    return {
        'modulos_permitidos': modulos_permitidos,
        'roles_activos':      roles_display,
        'rol_principal':      rol_principal,
    }
