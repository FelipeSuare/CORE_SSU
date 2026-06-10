from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.roles import obtener_roles
from employees.models import Funcionario

_ROLES_REPORTE_P = {'RRHH', 'Auditoria', 'Administrador'}


@login_required(login_url='login_home')
def reporte_general_view(request):
    roles = obtener_roles(request.user.username)
    if not (roles & _ROLES_REPORTE_P):
        return render(request, 'shared/sin_acceso.html', status=403)
    return render(request, 'reports/ReporteG.html')


@login_required(login_url='login_home')
def reporte_personal_view(request):
    roles = obtener_roles(request.user.username)
    if not (roles & _ROLES_REPORTE_P):
        return render(request, 'shared/sin_acceso.html', status=403)
    return render(request, 'reports/ReporteP.html')
