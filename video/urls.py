from django.urls import path

from video.views import (
    TemplateView, VideoView, VideoListView, VideoDetailView, VideoDeleteView, VideoUpdateView,
    VideoAssetUploadView, VideoAssetListView, VideoAssetDeleteView, VideoAssetPlayView, VideoAssetEditView,
    DraftListView, DraftDetailView, DraftDeleteView, VideoCoverUploadView
)

urlpatterns = [
    # 视频模板及生成视频
    path('templates/', TemplateView.as_view(), name='templates'),

    # 视频相关接口
    path('download/<str:video_id>/', VideoView.as_view(), name='download_video'),
    path('detail/<str:video_id>/', VideoDetailView.as_view(), name='video-detail'),
    path('', VideoListView.as_view(), name='video-list'),
    path('delete/', VideoDeleteView.as_view(), name='video-delete'),
    path('update/', VideoUpdateView.as_view(), name='video-update'),
    path('cover/upload/', VideoCoverUploadView.as_view(), name='video-cover-upload'),

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
