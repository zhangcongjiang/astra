from django.urls import path

from image.views import BindTagsToImageAPIView, ImageListView, ImageUploadView, DeleteImagesAPIView, DeleteImageTagAPIView, ImageDetailView

urlpatterns = [
    path('bind-tags/', BindTagsToImageAPIView.as_view(), name='bind-tags'),
    path('images/', ImageListView.as_view(), name='image-list'),
    path('upload/', ImageUploadView.as_view(), name='image-upload'),
    path('images/<uuid:image_id>/', DeleteImagesAPIView.as_view(), name='delete-image'),
    path('images/delete-tag/', DeleteImageTagAPIView.as_view(), name='delete-image-tag'),
    path('<uuid:id>/', ImageDetailView.as_view(), name='image-detail'),
]
