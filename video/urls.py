from django.urls import path

from video.views import TemplateView, VideoView, VideoProgressView
#
urlpatterns = [
    path('templates/', TemplateView.as_view(), name='templates'),
    path('download/<str:video_id>/', VideoView.as_view(), name='download_video'),
    path('process/<str:video_id>/', VideoProgressView.as_view(), name='video_process'),

]
