from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),   # suas APIs
    path("", include("web.urls")),       # tudo do front vai para o app 'web'
]
