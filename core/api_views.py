from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Feriado
from core.serializers import FeriadoSerializer
from core.api_permissions import NoCambioPendiente, EsRRHH, EsFuncionarioActivo


class FeriadosListView(APIView):
    permission_classes = [NoCambioPendiente, EsFuncionarioActivo]

    def get(self, request):
        anio = request.GET.get('anio', '').strip()
        tipo = request.GET.get('tipo', 'Todos').strip()

        qs = Feriado.objects.order_by('fecha')

        if anio:
            try:
                qs = qs.filter(fecha__year=int(anio))
            except ValueError:
                pass

        if tipo and tipo != 'Todos':
            qs = qs.filter(tipo=tipo)

        return Response({
            'feriados': [
                {
                    'id':          f.id_feriado,
                    'fecha':       f.fecha.strftime('%Y-%m-%d'),
                    'descripcion': f.descripcion,
                    'tipo':        f.tipo,
                }
                for f in qs
            ]
        })


class FeriadosCreateView(APIView):
    permission_classes = [NoCambioPendiente, EsRRHH]

    def post(self, request):
        serializer = FeriadoSerializer(data=request.data)
        if not serializer.is_valid():
            primer_error = next(iter(serializer.errors.values()))[0]
            return Response({'error': str(primer_error)}, status=status.HTTP_400_BAD_REQUEST)

        fecha       = serializer.validated_data['fecha']
        descripcion = serializer.validated_data['descripcion']
        tipo        = serializer.validated_data['tipo']

        if Feriado.objects.filter(fecha=fecha).exists():
            return Response(
                {'error': 'Ya existe un feriado registrado para esa fecha.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            feriado = Feriado.objects.create(fecha=fecha, descripcion=descripcion, tipo=tipo)
        except IntegrityError:
            return Response(
                {'error': 'Ya existe un feriado registrado para esa fecha.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'ok': True,
            'feriado': {
                'id':          feriado.id_feriado,
                'fecha':       feriado.fecha.strftime('%Y-%m-%d'),
                'descripcion': feriado.descripcion,
                'tipo':        feriado.tipo,
            },
        }, status=status.HTTP_201_CREATED)


class FeriadoEditView(APIView):
    permission_classes = [NoCambioPendiente, EsRRHH]

    def post(self, request, id_feriado):
        try:
            feriado = Feriado.objects.get(id_feriado=id_feriado)
        except Feriado.DoesNotExist:
            return Response({'error': 'Feriado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FeriadoSerializer(data=request.data)
        if not serializer.is_valid():
            primer_error = next(iter(serializer.errors.values()))[0]
            return Response({'error': str(primer_error)}, status=status.HTTP_400_BAD_REQUEST)

        fecha       = serializer.validated_data['fecha']
        descripcion = serializer.validated_data['descripcion']
        tipo        = serializer.validated_data['tipo']

        if Feriado.objects.filter(fecha=fecha).exclude(id_feriado=id_feriado).exists():
            return Response(
                {'error': 'Ya existe un feriado registrado para esa fecha.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        feriado.fecha       = fecha
        feriado.descripcion = descripcion
        feriado.tipo        = tipo
        try:
            feriado.save(update_fields=['fecha', 'descripcion', 'tipo'])
        except IntegrityError:
            return Response(
                {'error': 'Ya existe un feriado registrado para esa fecha.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'ok': True})


class FeriadoDeleteView(APIView):
    permission_classes = [NoCambioPendiente, EsRRHH]

    def post(self, request, id_feriado):
        try:
            feriado = Feriado.objects.get(id_feriado=id_feriado)
        except Feriado.DoesNotExist:
            return Response({'error': 'Feriado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        feriado.delete()
        return Response({'ok': True})
