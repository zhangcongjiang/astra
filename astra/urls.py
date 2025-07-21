"""
URL configuration for astra project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.authentication import TokenAuthentication

from astra.settings import MEDIA_URL, MEDIA_ROOT

schema_view = get_schema_view(
    openapi.Info(
        title="Django Sample Application API",
        default_version='v1',
        description="Welcome to the Django Sample Application API documentation",
    ),
    public=True,
    permission_classes=[permissions.AllowAny, ],
    authentication_classes=[TokenAuthentication, ],
)
urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('api/tag/', include('tag.urls')),
                  path('api/image/', include('image.urls')),
                  path('api/voice/', include('voice.urls')),
                  path('api/video/', include('video.urls')),
                  path('api/tool/', include('tools.urls')),
                  path('api/task/', include('task.urls')),
                  path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
                  path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
                  path('api/asset/', include('asset.urls')),
                  path('api/text/', include('text.urls')),
              ] + static(MEDIA_URL, document_root=MEDIA_ROOT)
