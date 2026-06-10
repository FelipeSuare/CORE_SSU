from django.test.runner import DiscoverRunner
from django.apps import apps as django_apps
from django.conf import settings


class ManagedTestRunner(DiscoverRunner):
    """
    Estrategia de test para modelos managed=False + migraciones RunSQL:

    1. Marca todos los modelos como managed=True para que syncdb cree las tablas.
    2. Deshabilita las migraciones de todas las apps locales para que el test DB
       se construya solo con syncdb (evita que RunSQL se ejecute antes de que
       existan las tablas que intenta modificar).
    3. Revierte ambas modificaciones tras crear/destruir la test DB.
    """

    # Apps cuyas migraciones hay que silenciar en tests.
    # None = "no hay módulo de migraciones para esta app" → Django usa syncdb.
    _LOCAL_APPS = [
        'accounts',
        'core',
        'dashboard',
        'employees',
        'reports',
        'vacations',
    ]

    def _set_managed(self, value: bool) -> None:
        for model in django_apps.get_models():
            model._meta.managed = value

    def _disable_migrations(self) -> dict:
        original = getattr(settings, 'MIGRATION_MODULES', {})
        settings.MIGRATION_MODULES = {app: None for app in self._LOCAL_APPS}
        return original

    def _restore_migrations(self, original: dict) -> None:
        if original:
            settings.MIGRATION_MODULES = original
        elif hasattr(settings, 'MIGRATION_MODULES'):
            del settings.MIGRATION_MODULES

    def setup_databases(self, **kwargs):
        self._set_managed(True)
        original_migrations = self._disable_migrations()
        try:
            result = super().setup_databases(**kwargs)
        finally:
            self._restore_migrations(original_migrations)
            self._set_managed(False)
        return result

    def teardown_databases(self, old_config, **kwargs):
        self._set_managed(True)
        original_migrations = self._disable_migrations()
        try:
            super().teardown_databases(old_config, **kwargs)
        finally:
            self._restore_migrations(original_migrations)
            self._set_managed(False)
