from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include  # ✅ include is required

def home(request):
    return JsonResponse({"message": "KitaabSe Backend is running."})

urlpatterns = [
    path('', home),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),  # ✅ users app URLs
]
