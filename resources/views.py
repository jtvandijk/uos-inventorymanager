from django.shortcuts import render


def hub(request):
    return render(request, 'resources/hub.html')
