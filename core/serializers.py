from rest_framework import serializers
from core.models import Feriado

TIPOS_FERIADO = ['Internacional', 'Nacional', 'Departamental', 'Municipal', 'Institucional']


class FeriadoSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    descripcion = serializers.CharField(max_length=200)
    tipo = serializers.ChoiceField(choices=TIPOS_FERIADO)
