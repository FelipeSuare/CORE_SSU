from django.core.management.base import BaseCommand

from employees.models import Funcionario
from vacations.utils import calcular_gestioneS_pendientes, poblar_gestion_vacacion


class Command(BaseCommand):
    help = (
        'Acredita automáticamente los días de vacación a todos los funcionarios activos '
        'según la Ley General del Trabajo de Bolivia. '
        'Solo rellena slots vacíos; no sobreescribe datos existentes.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--cod',
            type=str,
            help='Procesar solo el funcionario con este código (opcional).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se haría sin aplicar cambios en la base de datos.',
        )

    def handle(self, *args, **options):
        qs = Funcionario.objects.select_related('ci').filter(estado='ACTIVO')
        if options['cod']:
            qs = qs.filter(cod_funcionario=options['cod'])
            if not qs.exists():
                self.stderr.write(self.style.ERROR(f"No se encontró funcionario con código: {options['cod']}"))
                return

        total = acreditados = omitidos = sin_elegibilidad = 0

        for f in qs:
            total += 1
            nombre = f"{f.ci.nombre} {f.ci.ap_paterno}".strip()
            gestioneS = calcular_gestioneS_pendientes(f.fecha_ingreso)

            if not gestioneS:
                self.stdout.write(f'  — {nombre}: sin antigüedad suficiente, omitido.')
                sin_elegibilidad += 1
                continue

            if options['dry_run']:
                lineas = ', '.join(f'Gestión {anio}: {float(dias):.0f} días (slot {slot})' for slot, anio, dias in gestioneS)
                self.stdout.write(f'  [DRY-RUN] {nombre}: {lineas}')
                continue

            stats = poblar_gestion_vacacion(f)
            if stats['acreditadas'] > 0:
                acreditados += 1
                lineas = ', '.join(
                    f'Gestión {anio}: {float(dias):.0f} días'
                    for _, anio, dias in gestioneS
                )
                self.stdout.write(self.style.SUCCESS(f'  OK {nombre}: {lineas}'))
            else:
                omitidos += 1
                self.stdout.write(f'  — {nombre}: todas las gestiones ya estaban acreditadas.')

        if not options['dry_run']:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f'Listo. Total: {total} | Acreditados: {acreditados} | '
                f'Ya completos: {omitidos} | Sin elegibilidad: {sin_elegibilidad}'
            ))
