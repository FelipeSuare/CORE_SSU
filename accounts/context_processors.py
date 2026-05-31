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
      modulos_permitidos      — set de url_names accesibles por el usuario actual
      roles_activos           — lista de roles del usuario (sin 'Funcionario' si tiene otros)
      rol_principal           — rol más representativo para mostrar en UI
      nombre_completo_usuario — nombre completo desde la tabla persona
      cargo_actual_usuario    — cargo vigente desde historial_cargo
      descripcion_rol_principal — descripción del rol principal desde la tabla roles
    """
    if not request.user.is_authenticated:
        return {
            'modulos_permitidos':        frozenset(),
            'roles_activos':             [],
            'rol_principal':             '',
            'nombre_completo_usuario':   '',
            'cargo_actual_usuario':      '',
            'descripcion_rol_principal': '',
        }

    from core.middleware import _obtener_roles
    from core.permissions import PERMISOS, URL_ABIERTAS, PRIORIDAD_ROL
    from employees.models import Funcionario, HistorialCargo
    from accounts.models import Roles

    roles = _obtener_roles(request)

    modulos_permitidos = URL_ABIERTAS | {
        nombre
        for nombre, permitidos in PERMISOS.items()
        if roles & permitidos
    }

    rol_principal = next((r for r in PRIORIDAD_ROL if r in roles), 'Funcionario')
    roles_display = sorted(roles - {'Funcionario'}) if len(roles) > 1 else ['Funcionario']

    # Nombre completo y cargo actual desde la BD
    nombre_completo_usuario   = ''
    cargo_actual_usuario      = ''
    descripcion_rol_principal = ''

    try:
        f = Funcionario.objects.select_related('ci').get(
            ci__ci=request.user.username, estado='ACTIVO'
        )
        p = f.ci
        nombre_completo_usuario = f"{p.nombre} {p.ap_paterno} {p.ap_materno or ''}".strip()

        hc = HistorialCargo.objects.filter(cod_funcionario=f, es_actual=True).first()
        if hc:
            cargo_actual_usuario = hc.cargo
    except (Funcionario.DoesNotExist, Exception):
        pass

    try:
        rol_obj = Roles.objects.get(tipo_rol=rol_principal)
        descripcion_rol_principal = rol_obj.descripcion or ''
    except (Roles.DoesNotExist, Exception):
        pass

    return {
        'modulos_permitidos':        modulos_permitidos,
        'roles_activos':             roles_display,
        'rol_principal':             rol_principal,
        'nombre_completo_usuario':   nombre_completo_usuario,
        'cargo_actual_usuario':      cargo_actual_usuario,
        'descripcion_rol_principal': descripcion_rol_principal,
    }
