from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScheduledTaskViewSet

router = DefaultRouter()
router.register(r'task', ScheduledTaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),

    # 任务详情接口（已包含在ViewSet中）
    # 任务控制接口
    path('task/<uuid:pk>/pause/',
         ScheduledTaskViewSet.as_view({'post': 'pause'}),
         name='task-pause'),

    path('task/<uuid:pk>/resume/',
         ScheduledTaskViewSet.as_view({'post': 'resume'}),
         name='task-resume'),

    path('task/<uuid:pk>/run-now/',
         ScheduledTaskViewSet.as_view({'post': 'run_now'}),
         name='task-run-now'),
]