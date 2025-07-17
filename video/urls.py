from django.urls import path

from video.views import TemplateView, VideoView, VideoListView, VideoDetailView

#
urlpatterns = [
    path('templates/', TemplateView.as_view(), name='templates'),
    path('download/<str:video_id>/', VideoView.as_view(), name='download_video'),
    path('<str:video_id>/', VideoDetailView.as_view(), name='video-detail'),
    path('', VideoListView.as_view(), name='video-list'),
]
