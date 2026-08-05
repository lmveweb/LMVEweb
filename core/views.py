from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render

from .models import MensajePatrocinio


def home(request):
    return render(request, 'core/home.html')

def proyecto(request):
    return render(request, 'core/proyecto.html')

def impacto(request):
    return render(request, 'core/impacto.html')

def archivo(request):
    return render(request, 'core/archivo.html')


def redes(request):
    return render(request, 'core/redes.html')

def contacto(request):
    if request.method == 'POST':
        empresa = request.POST.get('empresa', '').strip()
        contacto_nombre = request.POST.get('contacto', '').strip()
        email = request.POST.get('email', '').strip()
        interes = request.POST.get('interes', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()

        errores = []
        if not empresa:
            errores.append('Falta el nombre de la empresa o marca.')
        if not contacto_nombre:
            errores.append('Falta la persona de contacto.')
        if not email:
            errores.append('Falta el correo electrónico.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errores.append('El correo electrónico no es válido.')
        if interes not in MensajePatrocinio.NivelInteres.values:
            errores.append('El nivel de interés no es válido.')

        if errores:
            return JsonResponse({'ok': False, 'errores': errores}, status=400)

        MensajePatrocinio.objects.create(
            empresa=empresa,
            contacto=contacto_nombre,
            email=email,
            interes=interes,
            mensaje=mensaje,
        )
        return JsonResponse({'ok': True})

    return render(request, 'core/contacto.html')