from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.modeling.urls')),
    path('api/', include('apps.archive.urls')),
    path('api/', include('apps.auth.urls')),
]
