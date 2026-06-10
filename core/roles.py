"""
Fuente única para obtener los roles de un usuario autenticado.
Usado por el middleware de acceso, las vistas legacy y las vistas DRF.
"""

import logging

logger = logging.getLogger('ssu.acceso_denegado')


def obtener_roles(username: str) -> set:
    """Devuelve el conjunto de roles activos del funcionario dado su CI."""
    from employees.models import Funcionario
    from accounts.models import FuncionarioRol

    try:
        funcionario = Funcionario.objects.get(ci__ci=username, estado='ACTIVO')
        roles = set(
            FuncionarioRol.objects
            .filter(cod_funcionario=funcionario, activo=True)
            .values_list('id_roles__tipo_rol', flat=True)
        )
    except Funcionario.DoesNotExist:
        roles = set()
    except Exception:
        logger.error('Error al obtener roles para %s', username, exc_info=True)
        roles = set()

    roles.add('Funcionario')
    return roles
