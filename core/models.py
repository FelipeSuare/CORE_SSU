from django.db import models


class IntentosAcceso(models.Model):
    """Auditoría de accesos denegados por falta de permisos."""
    username  = models.CharField(max_length=50)
    path      = models.CharField(max_length=255)
    url_name  = models.CharField(max_length=100, blank=True)
    roles     = models.CharField(max_length=255, blank=True)
    ip        = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intentos_acceso'
        ordering  = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%d/%m/%Y %H:%M} | {self.username} → {self.path}"


class UnidadOrganizacional(models.Model):
    id_unidad = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'unidad_organizacional'
        managed = False

class Feriado(models.Model):
    TIPO_CHOICES = [
        ('Internacional', 'Internacional'),
        ('Nacional', 'Nacional'),
        ('Departamental', 'Departamental'),
        ('Municipal', 'Municipal'),
        ('Institucional', 'Institucional'),
    ]
    id_feriado = models.AutoField(primary_key=True)
    fecha = models.DateField(unique=True)
    descripcion = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    class Meta:
        db_table = 'feriado'
        managed = False
