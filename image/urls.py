from django.urls import path

from image.views import BindTagsToImageAPIView, ImageListView, ImageUploadView, DeleteImageAPIView

urlpatterns = [
    path('bind-tags/', BindTagsToImageAPIView.as_view(), name='bind-tags'),
    path('images/', ImageListView.as_view(), name='image-list'),
    path('upload/', ImageUploadView.as_view(), name='image-upload'),
    path('images/<uuid:image_id>/', DeleteImageAPIView.as_view(), name='delete-image'),
]
