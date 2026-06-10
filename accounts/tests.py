import json
from datetime import date

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase, Client

from core.test_utils import hacer_usuario_y_funcionario


class TestCambiarContrasenaView(TestCase):
    """
    POST /Contrasena.html — la vista usa json.loads(request.body)
    con campos: actual, nueva, confirmar.
    Requiere contraseña fuerte: 8+ chars, mayúsculas, minúsculas, dígito, símbolo.
    """

    def setUp(self):
        self.user, self.func = hacer_usuario_y_funcionario(
            ci='77777777', nombre='Rosa', fecha_ingreso=date(2022, 1, 1)
        )
        # Contraseña inicial del func en Django User
        self.user.set_password('Inicial#123')
        self.user.save()
        # Sincronizar contrasena_hash con la contraseña inicial
        self.func.contrasena_hash = 'Inicial#123'
        self.func.save(update_fields=['contrasena_hash'])

        self.django_client = Client()
        self.django_client.force_login(self.user)
        self.url = reverse('contrasena')

    def _post_json(self, payload):
        return self.django_client.post(
            self.url,
            json.dumps(payload),
            content_type='application/json',
        )

    def test_get_devuelve_200(self):
        r = self.django_client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_cambio_exitoso_devuelve_ok(self):
        r = self._post_json({
            'actual':    'Inicial#123',
            'nueva':     'NuevaSegura456!',
            'confirmar': 'NuevaSegura456!',
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get('ok'))

    def test_contrasena_actual_incorrecta_devuelve_400(self):
        r = self._post_json({
            'actual':    'ContrasenaMal123!',
            'nueva':     'NuevaSegura456!',
            'confirmar': 'NuevaSegura456!',
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', r.json())

    def test_confirmacion_no_coincide_devuelve_400(self):
        r = self._post_json({
            'actual':    'Inicial#123',
            'nueva':     'NuevaSegura456!',
            'confirmar': 'OtraDistinta789!',
        })
        self.assertEqual(r.status_code, 400)

    def test_nueva_contrasena_debil_devuelve_400(self):
        # Sin símbolo especial → no pasa el patrón
        r = self._post_json({
            'actual':    'Inicial#123',
            'nueva':     'solominusculas',
            'confirmar': 'solominusculas',
        })
        self.assertEqual(r.status_code, 400)

    def test_requiere_autenticacion_redirige(self):
        cliente_anon = Client()
        r = cliente_anon.post(
            self.url,
            json.dumps({'actual': 'x', 'nueva': 'y', 'confirmar': 'y'}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 302)


class TestForzarCambioContrasena(TestCase):
    """
    Cuando la sesión tiene debe_cambiar_contrasena=True, el middleware
    redirige cualquier URL (excepto /Contrasena.html y login) a la página de cambio.
    """

    def setUp(self):
        self.user, self.func = hacer_usuario_y_funcionario(
            ci='88888888', nombre='Luis', fecha_ingreso=date(2021, 6, 1)
        )
        self.django_client = Client()
        self.django_client.force_login(self.user)

    def _forzar_flag(self):
        session = self.django_client.session
        session['debe_cambiar_contrasena'] = True
        session.save()

    def test_sin_flag_accede_normalmente(self):
        r = self.django_client.get(reverse('index'))
        # Sin flag el middleware no redirige
        self.assertNotEqual(r.status_code, 302)

    def test_con_flag_redirige_a_contrasena(self):
        self._forzar_flag()
        r = self.django_client.get(reverse('index'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('contrasena'), r['Location'])

    def test_con_flag_permite_acceder_a_contrasena(self):
        self._forzar_flag()
        r = self.django_client.get(reverse('contrasena'))
        self.assertNotEqual(r.status_code, 302)

    def test_con_flag_permite_acceder_a_login(self):
        self._forzar_flag()
        r = self.django_client.get(reverse('login_home'))
        self.assertNotEqual(r.status_code, 302)

    def test_despues_de_cambiar_flag_se_limpia(self):
        self._forzar_flag()
        # Después de cambiar contraseña exitosamente, el flag debe desaparecer
        # Lo verificamos directamente seteando el hash y llamando a la vista
        self.func.contrasena_hash = 'Inicial#123'
        self.func.save(update_fields=['contrasena_hash'])
        self.user.set_password('Inicial#123')
        self.user.save()
        self.django_client.force_login(self.user)
        self._forzar_flag()

        self.django_client.post(
            reverse('contrasena'),
            json.dumps({
                'actual':    'Inicial#123',
                'nueva':     'NuevaSegura456!',
                'confirmar': 'NuevaSegura456!',
            }),
            content_type='application/json',
        )

        session = self.django_client.session
        self.assertNotIn('debe_cambiar_contrasena', session)


class TestRecuperarContrasenaView(APITestCase):
    """POST /recuperar/verificar/ — AllowAny (sin autenticación requerida)."""

    url = '/recuperar/verificar/'

    def test_accesible_sin_autenticacion(self):
        r = self.client.post(self.url, {'ci': '00000000', 'fecha_nacimiento': '1990-01-01'})
        self.assertNotIn(r.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_ci_inexistente_devuelve_error(self):
        r = self.client.post(self.url, {'ci': 'NOEXISTE', 'fecha_nacimiento': '1990-01-01'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
