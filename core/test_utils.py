"""
Factories compartidas para tests de integración.
Crea el grafo Persona → Funcionario → User + opcionales (Roles, GestionVacacion).
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from accounts.models import FuncionarioRol, Roles
from core.models import UnidadOrganizacional
from employees.models import Funcionario, HistorialCargo, Persona
from vacations.models import GestionVacacion


def hacer_unidad(nombre='Unidad Test') -> UnidadOrganizacional:
    obj, _ = UnidadOrganizacional.objects.get_or_create(
        nombre=nombre, defaults={'activo': True}
    )
    return obj


def hacer_funcionario(
    ci: str = '12345678',
    nombre: str = 'Juan',
    ap_paterno: str = 'García',
    fecha_nacimiento: date = date(1990, 6, 15),
    fecha_ingreso: date = date(2020, 1, 1),
    tipo: str = 'PERSONAL DE AREA',
    unidad: UnidadOrganizacional = None,
) -> Funcionario:
    p = Persona.objects.create(
        ci=ci,
        nombre=nombre,
        ap_paterno=ap_paterno,
        fecha_nacimiento=fecha_nacimiento,
        sexo='Masculino',
    )
    return Funcionario.objects.create(
        cod_funcionario=f'F{ci}',
        ci=p,
        id_unidad=unidad or hacer_unidad(),
        fecha_ingreso=fecha_ingreso,
        tipo_funcionario=tipo,
        estado='ACTIVO',
        contrasena_hash='test',
    )


def hacer_usuario_y_funcionario(
    ci: str = '12345678',
    nombre: str = 'Juan',
    fecha_ingreso: date = date(2020, 1, 1),
    tipo: str = 'PERSONAL DE AREA',
    roles: list = None,
) -> tuple[User, Funcionario]:
    f    = hacer_funcionario(ci=ci, nombre=nombre, fecha_ingreso=fecha_ingreso, tipo=tipo)
    user = User.objects.create_user(username=ci, password='testpass123')

    for rol_nombre in (roles or []):
        rol, _ = Roles.objects.get_or_create(tipo_rol=rol_nombre)
        FuncionarioRol.objects.create(cod_funcionario=f, id_roles=rol, activo=True)

    return user, f


def hacer_gestion(
    funcionario: Funcionario,
    anio1: int = None,
    dias1: Decimal = Decimal('15'),
) -> GestionVacacion:
    gv = GestionVacacion.objects.create(
        cod_funcionario=funcionario,
        anio_gestion1=anio1,
        dias_gestion1=dias1,
    )
    gv.refresh_from_db()
    return gv


def hacer_cargo(
    funcionario: Funcionario,
    cargo: str = 'Analista',
    tipo_contrato: str = 'Fijo',
) -> HistorialCargo:
    return HistorialCargo.objects.create(
        cod_funcionario=funcionario,
        cargo=cargo,
        tipo_contrato=tipo_contrato,
        fecha_inicio=funcionario.fecha_ingreso,
        es_actual=True,
    )
