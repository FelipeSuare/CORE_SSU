"""
Handler centralizado de excepciones para vistas DRF.
Evita exponer tracebacks internos al cliente.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('ssu.acceso_denegado')


def manejar_excepcion(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return response

    # Excepción no controlada por DRF → 500 genérico sin exponer detalles
    logger.error(
        'Excepción no controlada en %s',
        context.get('view', '?'),
        exc_info=exc,
    )
    return Response(
        {'error': 'Error interno del servidor. Por favor contacta al administrador.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
