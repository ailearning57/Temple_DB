from django.shortcuts import render
from .models import TempleInfo

def home(request):
    info = TempleInfo.objects.first()
    return render(request, 'core/home.html', {'info': info})
