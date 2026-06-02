from django.apps import AppConfig


class VacationsConfig(AppConfig):
    name = 'vacations'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_auto_poblar_vacaciones, sender=self)


def _auto_poblar_vacaciones(sender, **kwargs):
    """
    Se ejecuta automáticamente después de 'manage.py migrate'.
    - Si el funcionario no tiene gestiones: las crea.
    - Si las tiene pero son incorrectas (algoritmo viejo) y nadie ha consumido
      días todavía: las corrige.
    - Si ya hay días consumidos: no toca nada (respeta el historial).
    """
    try:
        from decimal import Decimal
        from employees.models import Funcionario
        from vacations.models import GestionVacacion
        from vacations.utils import poblar_gestion_vacacion, calcular_gestioneS_pendientes

        for f in Funcionario.objects.filter(estado='ACTIVO'):
            esperadas = calcular_gestioneS_pendientes(f.fecha_ingreso)
            if not esperadas:
                continue  # Sin antigüedad suficiente

            try:
                gv = GestionVacacion.objects.get(cod_funcionario=f)

                # Años que deberían estar almacenados según el algoritmo correcto
                anios_esperados = {anio for _, anio, _ in esperadas}

                # Años que están almacenados actualmente
                anios_actuales = {
                    getattr(gv, f'anio_gestion{i}')
                    for i in range(1, 5)
                    if getattr(gv, f'anio_gestion{i}') is not None
                }

                if anios_actuales == anios_esperados:
                    continue  # Ya está correcto

                # Solo corregir si el funcionario nunca tuvo una solicitud aprobada
                # (significa que el saldo nunca fue tocado)
                from vacations.models import SolicitudVacacion
                if SolicitudVacacion.objects.filter(
                    cod_funcionario=f, estado='APROBADA'
                ).exists():
                    continue  # Ya consumió días, no tocar

                # Datos incorrectos y sin consumos: resetear y repoblar
                for i in range(1, 5):
                    setattr(gv, f'anio_gestion{i}', None)
                    setattr(gv, f'dias_gestion{i}', Decimal('0'))
                gv.save(update_fields=[
                    'anio_gestion1', 'dias_gestion1',
                    'anio_gestion2', 'dias_gestion2',
                    'anio_gestion3', 'dias_gestion3',
                    'anio_gestion4', 'dias_gestion4',
                ])
                poblar_gestion_vacacion(f)

            except GestionVacacion.DoesNotExist:
                poblar_gestion_vacacion(f)

    except Exception:
        pass  # No interrumpir migrate si la DB aún no está lista
