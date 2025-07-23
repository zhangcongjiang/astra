from django.urls import path

from video.views import (
    TemplateView, VideoView, VideoListView, VideoDetailView, VideoDeleteView,
    VideoAssetUploadView, VideoAssetListView, VideoAssetDeleteView, VideoAssetPlayView, VideoAssetEditView,
    DraftListView, DraftDetailView, DraftDeleteView
)

urlpatterns = [
    path('templates/', TemplateView.as_view(), name='templates'),
    path('download/<str:video_id>/', VideoView.as_view(), name='download_video'),
    path('detail/<str:video_id>/', VideoDetailView.as_view(), name='video-detail'),
    path('', VideoListView.as_view(), name='video-list'),
    path('delete/', VideoDeleteView.as_view(), name='video-delete'),
    
    # 视频素材相关接口
    path('assets/upload/', VideoAssetUploadView.as_view(), name='video-asset-upload'),
    path('assets/', VideoAssetListView.as_view(), name='video-asset-list'),
    path('assets/delete/', VideoAssetDeleteView.as_view(), name='video-asset-delete'),
    path('assets/edit/', VideoAssetEditView.as_view(), name='video-asset-edit'),
    path('assets/play/<str:asset_id>/', VideoAssetPlayView.as_view(), name='video-asset-play'),
    
    # 草稿相关接口
    path('drafts/delete/', DraftDeleteView.as_view(), name='draft-delete'),
    path('drafts/<str:draft_id>/', DraftDetailView.as_view(), name='draft-detail'),
    path('drafts/', DraftListView.as_view(), name='draft-list'),
]
