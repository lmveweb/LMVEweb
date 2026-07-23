from django.shortcuts import render

def home(request):
    return render(request, 'core/home.html')

def proyecto(request):
    return render(request, 'core/base.html')

def impacto(request):
    return render(request, 'core/base.html')

def redes(request):
    return render(request, 'core/base.html')

def contacto(request):
    return render(request, 'core/base.html')