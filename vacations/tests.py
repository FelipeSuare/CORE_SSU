from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase

from vacations.utils import (
    calcular_anios_antiguedad,
    calcular_gestioneS_pendientes,
    dias_por_antiguedad,
)
from vacations.api_views import _calcular_retorno
from core.models import Feriado
from vacations.models import GestionVacacion, JerarquiaAprobacion, SolicitudVacacion
from core.test_utils import hacer_usuario_y_funcionario, hacer_gestion, hacer_cargo


# ══════════════════════════════════════════════════════════════════════════════
#  Funciones puras — no usan DB
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcularAniosAntiguedad(TestCase):
    """Años completos de servicio, incluyendo bordes de aniversario."""

    def test_exactamente_un_anio(self):
        self.assertEqual(calcular_anios_antiguedad(date(2020, 6, 15), date(2021, 6, 15)), 1)

    def test_un_dia_antes_del_aniversario(self):
        self.assertEqual(calcular_anios_antiguedad(date(2020, 6, 15), date(2021, 6, 14)), 0)

    def test_un_dia_despues_del_aniversario(self):
        self.assertEqual(calcular_anios_antiguedad(date(2020, 6, 15), date(2021, 6, 16)), 1)

    def test_cinco_anios_exactos(self):
        self.assertEqual(calcular_anios_antiguedad(date(2015, 1, 1), date(2020, 1, 1)), 5)

    def test_diez_anios_exactos(self):
        self.assertEqual(calcular_anios_antiguedad(date(2010, 3, 20), date(2020, 3, 20)), 10)

    def test_fecha_ingreso_hoy_cero_anios(self):
        hoy = date.today()
        self.assertEqual(calcular_anios_antiguedad(hoy, hoy), 0)

    def test_referencia_anterior_a_ingreso_devuelve_cero(self):
        self.assertEqual(calcular_anios_antiguedad(date(2025, 1, 1), date(2020, 1, 1)), 0)

    def test_bisiesto_29feb_ref_28feb_siguiente(self):
        # Ingresó en año bisiesto. El 28/02 del año siguiente NO es su aniversario.
        self.assertEqual(calcular_anios_antiguedad(date(2020, 2, 29), date(2021, 2, 28)), 0)

    def test_bisiesto_29feb_ref_01mar_siguiente(self):
        self.assertEqual(calcular_anios_antiguedad(date(2020, 2, 29), date(2021, 3, 1)), 1)

    def test_quince_anios(self):
        self.assertEqual(calcular_anios_antiguedad(date(2005, 7, 4), date(2020, 7, 4)), 15)


class TestDiasPorAntiguedad(TestCase):
    """Tabla LGT Bolivia: <1→0, 1-4→15, 5-9→20, 10+→30."""

    def test_cero_anios(self):
        self.assertEqual(dias_por_antiguedad(0), Decimal('0'))

    def test_un_anio(self):
        self.assertEqual(dias_por_antiguedad(1), Decimal('15'))

    def test_cuatro_anios(self):
        self.assertEqual(dias_por_antiguedad(4), Decimal('15'))

    def test_cinco_anios_exactos_salta_a_20(self):
        self.assertEqual(dias_por_antiguedad(5), Decimal('20'))

    def test_nueve_anios(self):
        self.assertEqual(dias_por_antiguedad(9), Decimal('20'))

    def test_diez_anios_exactos_salta_a_30(self):
        self.assertEqual(dias_por_antiguedad(10), Decimal('30'))

    def test_veinte_anios(self):
        self.assertEqual(dias_por_antiguedad(20), Decimal('30'))


class TestCalcularRetorno(TestCase):
    """
    Cálculo de fecha de retorno avanzando días hábiles.
    fecha_retorno = primer día posterior al último día de vacación.
    """

    def _run(self, fecha_salida, dias, nacimiento=None, feriados=None):
        return _calcular_retorno(fecha_salida, dias, nacimiento, feriados or set())

    # ── Casos básicos ──────────────────────────────────────────────────────────

    def test_cinco_dias_desde_lunes(self):
        # Lun 8/1 → vie 12/1 (5 hábiles), sin fines de semana cruzados.
        # fecha_retorno = sáb 13/1 (primer día después del bloque)
        r = self._run(date(2024, 1, 8), Decimal('5'))
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 13))
        self.assertEqual(r['dias_fines_semana'], 0)
        self.assertEqual(r['dias_feriados'], 0)

    def test_cinco_dias_desde_jueves_cruza_fin_de_semana(self):
        # Jue 11/1 + vie 12/1 (2) + sáb-dom skip + lun 15 + mar 16 + mié 17/1 (5)
        r = self._run(date(2024, 1, 11), Decimal('5'))
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 18))
        self.assertEqual(r['dias_fines_semana'], 2)

    def test_un_dia_desde_sabado_salta_fin_de_semana(self):
        # Sáb 13/1 y dom 14/1 se saltean; primer hábil = lun 15/1
        r = self._run(date(2024, 1, 13), Decimal('1'))
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 16))
        self.assertEqual(r['dias_fines_semana'], 2)

    def test_quince_dias_desde_lunes(self):
        # 3 semanas exactas de lunes a viernes, 2 fines de semana cruzados (4 días)
        r = self._run(date(2024, 1, 8), Decimal('15'))
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 27))
        self.assertEqual(r['dias_fines_semana'], 4)

    # ── Feriados ───────────────────────────────────────────────────────────────

    def test_feriado_en_habil_extiende_vacation(self):
        # 5 hábiles desde lun 8/1, feriado el mié 10/1
        # Debe agregar 1 día extra: retorno = mar 16/1 en vez de sáb 13/1
        feriados = {date(2024, 1, 10)}
        r = self._run(date(2024, 1, 8), Decimal('5'), feriados=feriados)
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 16))
        self.assertEqual(r['dias_feriados'], 1)
        self.assertEqual(r['dias_fines_semana'], 2)

    def test_dos_feriados_extienden_vacation(self):
        # Jan 8(1) → Jan 9 feriado → Jan 10 feriado → Jan 11(2) → Jan 12(3)
        # → Sáb/Dom → Jan 15(4) → Jan 16(5) → retorno Jan 17
        feriados = {date(2024, 1, 9), date(2024, 1, 10)}
        r = self._run(date(2024, 1, 8), Decimal('5'), feriados=feriados)
        self.assertEqual(r['dias_feriados'], 2)
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 17))

    def test_feriado_en_fin_de_semana_no_cuenta(self):
        # Si el feriado cae en sábado no incrementa el contador (el sáb ya era no hábil)
        feriados = {date(2024, 1, 13)}  # sábado
        r_sin = self._run(date(2024, 1, 8), Decimal('5'))
        r_con = self._run(date(2024, 1, 8), Decimal('5'), feriados=feriados)
        # El sáb ya era skip por fin de semana, el feriado no añade días extras
        self.assertEqual(r_sin['fecha_retorno'], r_con['fecha_retorno'])
        self.assertEqual(r_con['dias_feriados'], 0)

    # ── Cumpleaños (medio asueto) ───────────────────────────────────────────────

    def test_cumpleanios_en_primer_dia_agrega_medio_dia(self):
        nacimiento = date(1990, 1, 8)  # cumple el 8 de enero
        # Sin cumpleaños: 1 hábil → retorno día siguiente (9/1)
        r_sin = self._run(date(2024, 1, 8), Decimal('1'))
        self.assertEqual(r_sin['fecha_retorno'], date(2024, 1, 9))
        # Con cumpleaños el 8/1 cuenta 0.5, después el 9/1 completa a 1.5 → retorno 10/1
        r_con = self._run(date(2024, 1, 8), Decimal('1'), nacimiento=nacimiento)
        self.assertEqual(r_con['fecha_retorno'], date(2024, 1, 10))
        self.assertEqual(r_con['dias_cumpleanos'], 1)

    def test_cumpleanios_fuera_del_periodo_no_afecta(self):
        # Cumpleaños el 31 de diciembre; vacaciones en enero → no hay efecto
        nacimiento = date(1990, 12, 31)
        r = self._run(date(2024, 1, 8), Decimal('5'), nacimiento=nacimiento)
        self.assertEqual(r['dias_cumpleanos'], 0)
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 13))

    # ── Días fraccionarios ─────────────────────────────────────────────────────

    def test_medio_dia_retorna_al_dia_siguiente(self):
        r = self._run(date(2024, 1, 8), Decimal('0.5'))
        # 0.5 hábiles: el lunes 8/1 cuenta 1 completo (0.5 < target no, sale)
        # Espera: habiles=1 > 0.5, retorno = 9/1
        self.assertEqual(r['fecha_retorno'], date(2024, 1, 9))


class TestCalcularGestionesPendientes(TestCase):
    """Asignación correcta de slots y gestiones elegibles."""

    def _hoy(self, s):
        return date.fromisoformat(s)

    def test_recien_ingresado_sin_elegibilidad(self):
        # Ingresó hace 6 meses, ninguna gestión con 1 año completo
        ingreso = date(2025, 1, 1)
        hoy     = date(2025, 6, 1)
        self.assertEqual(calcular_gestioneS_pendientes(ingreso, hoy), [])

    def test_exactamente_un_anio_slot_4(self):
        ingreso = date(2024, 6, 1)
        hoy     = date(2025, 6, 1)  # cumple 1 año hoy
        gs      = calcular_gestioneS_pendientes(ingreso, hoy)
        self.assertEqual(len(gs), 1)
        slot, anio, dias = gs[0]
        self.assertEqual(slot, 4)
        self.assertEqual(anio, 2025)
        self.assertEqual(dias, Decimal('15'))

    def test_cuatro_gestiones_slots_correctos(self):
        # 4 años completos → 4 gestiones, oldest en slot 4, newest en slot 1
        ingreso = date(2021, 6, 1)
        hoy     = date(2025, 6, 1)
        gs      = calcular_gestioneS_pendientes(ingreso, hoy)
        self.assertEqual(len(gs), 4)
        slots = [g[0] for g in gs]
        anios = [g[1] for g in gs]
        self.assertEqual(slots, [4, 3, 2, 1])
        self.assertEqual(anios, [2022, 2023, 2024, 2025])

    def test_diez_anios_da_30_dias(self):
        ingreso = date(2015, 6, 1)
        hoy     = date(2025, 6, 1)  # cumple 10 años
        gs      = calcular_gestioneS_pendientes(ingreso, hoy)
        # gestión 2025 debe tener 30 días (>= 10 años)
        gestiones_dict = {g[1]: g[2] for g in gs}
        self.assertEqual(gestiones_dict[2025], Decimal('30'))

    def test_limite_maximo_cuatro_gestiones(self):
        ingreso = date(2005, 1, 1)  # 20+ años
        hoy     = date(2025, 6, 1)
        gs      = calcular_gestioneS_pendientes(ingreso, hoy)
        self.assertLessEqual(len(gs), 4)

    def test_antes_del_aniversario_no_incluye_anio_actual(self):
        # Ingresó 15/06, hoy es 14/06 (día antes de aniversario)
        ingreso = date(2024, 6, 15)
        hoy     = date(2025, 6, 14)
        gs      = calcular_gestioneS_pendientes(ingreso, hoy)
        anios   = [g[1] for g in gs]
        self.assertNotIn(2025, anios)

    def test_anios_cinco_da_20_dias(self):
        ingreso = date(2020, 6, 1)
        hoy     = date(2025, 6, 1)  # 5 años exactos
        gs      = calcular_gestioneS_pendientes(ingreso, hoy)
        gestiones_dict = {g[1]: g[2] for g in gs}
        self.assertEqual(gestiones_dict.get(2025), Decimal('20'))


# ══════════════════════════════════════════════════════════════════════════════
#  Tests de API — requieren DB (usa ManagedTestRunner de settings.py)
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcularRetornoAPI(APITestCase):
    """POST /api/vacaciones/calcular-retorno/ — no requiere Funcionario."""

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('tester', password='pass')
        self.client.force_login(self.user)
        self.url = reverse('vac_calcular_retorno')

    def test_requiere_autenticacion(self):
        # SessionAuthentication sin sesión activa → 403 (sin WWW-Authenticate header)
        self.client.logout()
        r = self.client.post(self.url, {'fecha_salida': '2024-01-08', 'dias_solicitados': '5'})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_datos_incompletos_devuelve_400(self):
        r = self.client.post(self.url, {'fecha_salida': '2024-01-08'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fecha_invalida_devuelve_400(self):
        r = self.client.post(self.url, {'fecha_salida': 'no-es-fecha', 'dias_solicitados': '5'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dias_cero_devuelve_400(self):
        r = self.client.post(self.url, {'fecha_salida': '2024-01-08', 'dias_solicitados': '0'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cinco_dias_habiles_desde_lunes(self):
        r = self.client.post(self.url, {
            'fecha_salida': '2024-01-08',
            'dias_solicitados': '5',
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertEqual(data['fecha_retorno'], '2024-01-13')
        self.assertEqual(data['dias_fines_semana'], 0)
        self.assertEqual(data['dias_feriados'], 0)

    def test_cinco_dias_con_feriado_registrado(self):
        Feriado.objects.create(
            fecha=date(2024, 1, 10),
            descripcion='Feriado de prueba',
            tipo='Nacional',
        )
        r = self.client.post(self.url, {
            'fecha_salida': '2024-01-08',
            'dias_solicitados': '5',
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertEqual(data['dias_feriados'], 1)
        self.assertGreater(
            date.fromisoformat(data['fecha_retorno']),
            date(2024, 1, 13),
        )

    def test_respuesta_incluye_fecha_conclusion(self):
        r = self.client.post(self.url, {
            'fecha_salida': '2024-01-08',
            'dias_solicitados': '5',
        })
        data = r.json()
        retorno    = date.fromisoformat(data['fecha_retorno'])
        conclusion = date.fromisoformat(data['fecha_conclusion'])
        from datetime import timedelta
        self.assertEqual(conclusion, retorno - timedelta(days=1))


class TestDatosFormularioAPI(APITestCase):
    """GET /api/vacaciones/datos/ — requiere Funcionario activo + GestionVacacion."""

    def setUp(self):
        self.user, self.func = hacer_usuario_y_funcionario(
            ci='11111111',
            nombre='Ana',
            fecha_ingreso=date(2021, 1, 1),
        )
        hacer_cargo(self.func)
        self.gv = hacer_gestion(self.func, anio1=2024, dias1=Decimal('15'))
        self.client.force_login(self.user)
        self.url = reverse('vac_datos')

    def test_requiere_autenticacion(self):
        self.client.logout()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_devuelve_datos_del_funcionario(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertEqual(data['ci'], '11111111')
        self.assertIn('saldos', data)
        self.assertIn('gestiones', data['saldos'])

    def test_puede_solicitar_con_saldo(self):
        r = self.client.get(self.url)
        data = r.json()
        # Tiene 1 año+ de ingreso y saldo > 0 → puede solicitar
        self.assertTrue(data['puede_solicitar'])

    def test_funcionario_inexistente_devuelve_404(self):
        from django.contrib.auth.models import User
        otro_user = User.objects.create_user('99999999', password='pass')
        self.client.force_login(otro_user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class TestCrearSolicitudAPI(APITestCase):
    """POST /api/vacaciones/crear/ — valida saldo y crea solicitud."""

    def setUp(self):
        self.user, self.func = hacer_usuario_y_funcionario(
            ci='22222222',
            nombre='Pedro',
            fecha_ingreso=date(2020, 1, 1),
        )
        hacer_cargo(self.func)
        self.gv = hacer_gestion(self.func, anio1=2024, dias1=Decimal('15'))

        # Crear un aprobador para que la solicitud quede PENDIENTE (no APROBADA)
        _, self.aprobador = hacer_usuario_y_funcionario(
            ci='22222223', nombre='Jefe', roles=['Jefe de Area']
        )
        JerarquiaAprobacion.objects.create(
            cod_funcionario=self.func,
            cod_aprobador=self.aprobador,
            nivel_aprobacion=1,
            activo=True,
        )

        self.client.force_login(self.user)
        self.url = reverse('vac_crear')

    def _payload_valido(self, dias='5'):
        return {
            'fecha_salida':   '2025-02-03',
            'fecha_retorno':  '2025-02-10',
            'dias_solicitados': dias,
            'motivo_vacacion': 'Vacaciones anuales por descanso familiar',
        }

    def test_crear_solicitud_exitosa(self):
        r = self.client.post(self.url, self._payload_valido())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(r.json()['ok'])
        self.assertTrue(SolicitudVacacion.objects.filter(cod_funcionario=self.func).exists())

    def test_saldo_insuficiente_devuelve_400(self):
        r = self.client.post(self.url, self._payload_valido(dias='30'))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Saldo insuficiente', r.json()['error'])

    def test_motivo_muy_corto_devuelve_400(self):
        payload = self._payload_valido()
        payload['motivo_vacacion'] = 'Corto'
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_doble_solicitud_pendiente(self):
        # Primera solicitud queda PENDIENTE_JEFE (hay jerarquía)
        self.client.post(self.url, self._payload_valido())
        # Segunda solicitud debe rechazarse
        r2 = self.client.post(self.url, self._payload_valido())
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pendiente', r2.json()['error'])

    def test_sin_gestion_vacacion_devuelve_400(self):
        self.gv.delete()
        r = self.client.post(self.url, self._payload_valido())
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class TestMisSolicitudesAPI(APITestCase):
    """GET /api/vacaciones/mis-solicitudes/ — lista solicitudes del funcionario."""

    def setUp(self):
        self.user, self.func = hacer_usuario_y_funcionario(
            ci='33333333',
            nombre='Laura',
            fecha_ingreso=date(2019, 3, 1),
        )
        hacer_cargo(self.func)
        hacer_gestion(self.func, anio1=2024, dias1=Decimal('10'))
        self.client.force_login(self.user)
        self.url = reverse('vac_mis_solicitudes')

    def test_devuelve_lista_vacia_sin_solicitudes(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertEqual(data['solicitudes'], [])
        self.assertEqual(data['resumen']['total'], 0)

    def test_devuelve_solicitud_creada(self):
        SolicitudVacacion.objects.create(
            cod_funcionario=self.func,
            fecha_salida=date(2025, 2, 3),
            fecha_retorno=date(2025, 2, 10),
            dias_solicitados=Decimal('5'),
            motivo_vacacion='Vacaciones anuales',
            estado='APROBADA',
        )
        r = self.client.get(self.url)
        data = r.json()
        self.assertEqual(data['resumen']['total'], 1)
        self.assertEqual(data['solicitudes'][0]['estado'], 'Aprobada')


class TestHistorialRRHHAPI(APITestCase):
    """GET /api/vacaciones/historial-rrhh/ — solo accesible con rol RRHH."""

    def setUp(self):
        self.user_rrhh, self.func_rrhh = hacer_usuario_y_funcionario(
            ci='44444444', nombre='Carlos', roles=['RRHH']
        )
        self.user_normal, _ = hacer_usuario_y_funcionario(
            ci='55555555', nombre='Normal'
        )
        self.url = reverse('vac_historial_rrhh')

    def test_sin_rol_rrhh_devuelve_403(self):
        self.client.force_login(self.user_normal)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_con_rol_rrhh_devuelve_200(self):
        self.client.force_login(self.user_rrhh)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertIn('solicitudes', data)
        self.assertIn('usuario', data)
