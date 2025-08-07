from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ScheduledTaskViewSet

router = DefaultRouter()
router.register(r'', ScheduledTaskViewSet, basename='scheduledtask')

urlpatterns = [
    path('', include(router.urls)),
]