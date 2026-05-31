from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from accounts.models import FuncionarioRol
from core.models import UnidadOrganizacional
from employees.models import Funcionario, HistorialCargo
from vacations.models import GestionVacacion, SolicitudVacacion

_ROLES_REPORTE_P = {'RRHH', 'Auditoria', 'Administrador'}

_ROL_AREA_LABEL = {
    'RRHH':          'RECURSOS HUMANOS',
    'Auditoria':     'AUDITORIA',
    'Administrador': 'ADMINISTRACIÓN',
}


def _get_roles_usuario(request):
    ci = request.user.username
    try:
        f = Funcionario.objects.get(ci__ci=ci, estado='ACTIVO')
    except Funcionario.DoesNotExist:
        return set(), None
    roles = set(FuncionarioRol.objects.filter(
        cod_funcionario=f, activo=True
    ).values_list('id_roles__tipo_rol', flat=True))
    return roles, f


def _area_label_usuario(roles):
    for rol in ('Administrador', 'RRHH', 'Auditoria'):
        if rol in roles:
            return _ROL_AREA_LABEL[rol]
    return 'RECURSOS HUMANOS'


def _nombre_rrhh_activo():
    """Nombre de la persona con rol RRHH activo al momento de generar el PDF."""
    fr = FuncionarioRol.objects.filter(
        id_roles__tipo_rol='RRHH', activo=True
    ).select_related('cod_funcionario__ci').first()
    if not fr:
        return ''
    p = fr.cod_funcionario.ci
    return f"{p.nombre} {p.ap_paterno}"


# ──────────────────────────────────────────────────────────────
#  Página HTML
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login_home')
def reporte_general_view(request):
    roles, _ = _get_roles_usuario(request)
    if not (roles & _ROLES_REPORTE_P):
        return render(request, 'shared/sin_acceso.html', status=403)
    return render(request, 'reports/ReporteG.html')


@login_required(login_url='login_home')
def reporte_personal_view(request):
    roles, _ = _get_roles_usuario(request)
    if not (roles & _ROLES_REPORTE_P):
        return render(request, 'shared/sin_acceso.html', status=403)
    return render(request, 'reports/ReporteP.html')


# ──────────────────────────────────────────────────────────────
#  API: unidades organizacionales + contexto del usuario
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login_home')
def api_rp_unidades(request):
    roles, _ = _get_roles_usuario(request)
    if not (roles & _ROLES_REPORTE_P):
        return JsonResponse({'error': 'Sin acceso.'}, status=403)

    unidades = list(
        UnidadOrganizacional.objects.filter(activo=True)
        .order_by('nombre')
        .values('id_unidad', 'nombre')
    )
    return JsonResponse({
        'unidades':    unidades,
        'area_label':  _area_label_usuario(roles),
        'nombre_rrhh': _nombre_rrhh_activo(),
    })


# ──────────────────────────────────────────────────────────────
#  API: lista de funcionarios con gestiones de vacaciones
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login_home')
def api_rp_funcionarios(request):
    roles, _ = _get_roles_usuario(request)
    if not (roles & _ROLES_REPORTE_P):
        return JsonResponse({'error': 'Sin acceso.'}, status=403)

    unidad_id = request.GET.get('unidad', '').strip()
    tipo_cont = request.GET.get('tipo_contrato', '').strip()
    nombre_b  = request.GET.get('funcionario', '').strip()

    qs = Funcionario.objects.filter(estado='ACTIVO').select_related('ci', 'id_unidad')

    if unidad_id:
        qs = qs.filter(id_unidad=unidad_id)

    if tipo_cont:
        cods_tipo = list(HistorialCargo.objects.filter(
            es_actual=True, tipo_contrato=tipo_cont
        ).values_list('cod_funcionario', flat=True))
        qs = qs.filter(cod_funcionario__in=cods_tipo)

    if nombre_b:
        qs = qs.filter(
            Q(ci__nombre__icontains=nombre_b) |
            Q(ci__ap_paterno__icontains=nombre_b)
        )

    funcionarios = list(qs.order_by('ci__ap_paterno', 'ci__nombre'))
    cods = [f.cod_funcionario for f in funcionarios]

    cargos_map = {
        hc.cod_funcionario_id: hc
        for hc in HistorialCargo.objects.filter(cod_funcionario__in=cods, es_actual=True)
    }
    gestiones_map = {
        gv.cod_funcionario_id: gv
        for gv in GestionVacacion.objects.filter(cod_funcionario__in=cods)
    }

    result = []
    for f in funcionarios:
        hc = cargos_map.get(f.cod_funcionario)
        gv = gestiones_map.get(f.cod_funcionario)
        am = f.ci.ap_materno or ''

        gestiones = []
        for i in range(1, 5):
            anio = getattr(gv, f'anio_gestion{i}', None) if gv else None
            dias = float(getattr(gv, f'dias_gestion{i}') or 0) if gv else 0.0
            gestiones.append({'anio': anio, 'dias': dias})

        result.append({
            'cod':              f.cod_funcionario,
            'nombre_completo':  f"{f.ci.nombre} {f.ci.ap_paterno} {am}".strip(),
            'apellidos_nombres':f"{f.ci.ap_paterno} {am} {f.ci.nombre}".strip(),
            'nombre_firma':     f"{f.ci.nombre} {f.ci.ap_paterno}",
            'cargo':            hc.cargo if hc else '',
            'tipo_contrato':    hc.tipo_contrato if hc else '',
            'unidad':           f.id_unidad.nombre if f.id_unidad else '',
            'fecha_ingreso':    f.fecha_ingreso.strftime('%d/%m/%Y') if f.fecha_ingreso else '',
            'gestiones':        gestiones,
            'dias_negados':     float(gv.dias_negados) if gv else 0.0,
            'dias_adeudados':   float(gv.dias_adeudados or 0) if gv else 0.0,
        })

    return JsonResponse({'funcionarios': result, 'total': len(result)})


# ──────────────────────────────────────────────────────────────
#  API: historial de solicitudes aprobadas de un funcionario
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login_home')
def api_rp_historial(request):
    roles, _ = _get_roles_usuario(request)
    if not (roles & _ROLES_REPORTE_P):
        return JsonResponse({'error': 'Sin acceso.'}, status=403)

    cod = request.GET.get('cod', '').strip()
    if not cod:
        return JsonResponse({'error': 'Falta cod.'}, status=400)

    try:
        f = Funcionario.objects.select_related('ci', 'id_unidad').get(
            cod_funcionario=cod, estado='ACTIVO'
        )
    except Funcionario.DoesNotExist:
        return JsonResponse({'error': 'Funcionario no encontrado.'}, status=404)

    hc = HistorialCargo.objects.filter(cod_funcionario=f, es_actual=True).first()
    gv = GestionVacacion.objects.filter(cod_funcionario=f).first()

    solicitudes = SolicitudVacacion.objects.filter(
        cod_funcionario=f, estado='APROBADA'
    ).order_by('fecha_salida')

    historial = {}
    for sol in solicitudes:
        anio = str(sol.fecha_salida.year)
        if anio not in historial:
            historial[anio] = []
        historial[anio].append({
            'inicio': sol.fecha_salida.strftime('%d/%m/%Y'),
            'fin':    sol.fecha_retorno.strftime('%d/%m/%Y'),
            'dias':   float(sol.dias_solicitados),
        })

    for sols in historial.values():
        for i, s in enumerate(sols):
            s['nro'] = i + 1

    am = f.ci.ap_materno or ''
    return JsonResponse({
        'cod':               f.cod_funcionario,
        'nombre_completo':   f"{f.ci.nombre} {f.ci.ap_paterno} {am}".strip(),
        'apellidos_nombres': f"{f.ci.ap_paterno} {am} {f.ci.nombre}".strip(),
        'nombre_firma':      f"{f.ci.nombre} {f.ci.ap_paterno}",
        'cargo':             hc.cargo if hc else '',
        'fecha_ingreso':     f.fecha_ingreso.strftime('%d/%m/%Y') if f.fecha_ingreso else '',
        'dias_adeudados':    float(gv.dias_adeudados or 0) if gv else 0.0,
        'historial':         historial,
    })
