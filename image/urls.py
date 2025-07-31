from django.urls import path
from .views import  ImageInfoAPIView

from image.views import BindTagsToImageAPIView, ImageListView, ImageUploadView, DeleteImagesAPIView, ImageDetailView

urlpatterns = [
    path('<uuid:id>/', ImageDetailView.as_view(), name='image-detail'),
    path('bind-tags/', BindTagsToImageAPIView.as_view(), name='bind-tags'),
    path('', ImageListView.as_view(), name='image-list'),
    path('upload/', ImageUploadView.as_view(), name='image-upload'),
    path('delete/', DeleteImagesAPIView.as_view(), name='delete-image'),
    path('<uuid:image_id>/detail/', ImageInfoAPIView.as_view(), name='image-info'),
]
