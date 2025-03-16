from django.urls import path

from voice.views import BindTagsToSoundAPIView, SoundListView, SoundUploadView, DeleteSoundsAPIView, DeleteSoundTagAPIView, SoundDetailView

urlpatterns = [

    path('bind-tags/', BindTagsToSoundAPIView.as_view(), name='bind-tags'),
    path('', SoundListView.as_view(), name='sound-list'),
    path('upload/', SoundUploadView.as_view(), name='sound-upload'),
    path('<uuid:sound_id>/', DeleteSoundsAPIView.as_view(), name='delete-sound'),
    path('delete-tag/', DeleteSoundTagAPIView.as_view(), name='delete-sound-tag'),
    path('<uuid:id>/', SoundDetailView.as_view(), name='sound-detail'),
]
