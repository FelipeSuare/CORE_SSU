from datetime import date
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

TIPOS_FERIADO = ['Internacional', 'Nacional', 'Departamental', 'Municipal', 'Institucional']


@login_required(login_url='login_home')
def feriados_view(request):
    return render(request, 'core/Feriados.html', {
        'anio_actual': date.today().year,
        'tipos': TIPOS_FERIADO,
    })
