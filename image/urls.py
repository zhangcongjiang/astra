from django.urls import path
from .views import ImageContentAPIView, ImageInfoAPIView

from image.views import BindTagsToImageAPIView, ImageListView, ImageUploadView, DeleteImagesAPIView, DeleteImageTagAPIView, ImageDetailView

urlpatterns = [
    path('bind-tags/', BindTagsToImageAPIView.as_view(), name='bind-tags'),
    path('', ImageListView.as_view(), name='image-list'),
    path('upload/', ImageUploadView.as_view(), name='image-upload'),
    path('<uuid:image_id>/', DeleteImagesAPIView.as_view(), name='delete-image'),
    path('delete-tag/', DeleteImageTagAPIView.as_view(), name='delete-image-tag'),
    path('<uuid:id>/', ImageDetailView.as_view(), name='image-detail'),
    path('<uuid:image_id>/content/', ImageContentAPIView.as_view(), name='image-content'),
    path('<uuid:image_id>/info/', ImageInfoAPIView.as_view(), name='image-info'),
]
