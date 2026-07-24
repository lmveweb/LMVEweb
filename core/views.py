from django.shortcuts import render

def home(request):
    return render(request, 'core/home.html')

def proyecto(request):
    return render(request, 'core/proyecto.html')

def impacto(request):
    return render(request, 'core/impacto.html')

def redes(request):
    return render(request, 'core/redes.html')

def contacto(request):
    return render(request, 'core/contacto.html')