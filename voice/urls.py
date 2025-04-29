from django.urls import path

from voice.views import BindTagsToSoundAPIView, SoundListView, SoundUploadView, DeleteSoundsAPIView, DeleteSoundTagAPIView, SoundDetailView, \
    SpeakerListAPIView, RegenerateSoundAPIView, SpeakerCreateAPIView, DeleteSpeakerAPIView, UpdateSpeakerAPIView, GenerateSoundAPIView, \
    SpeakerSampleAudioAPIView

urlpatterns = [
    path('bind-tags/', BindTagsToSoundAPIView.as_view(), name='bind-tags'),
    path('', SoundListView.as_view(), name='sound-list'),
    path('upload/', SoundUploadView.as_view(), name='sound-upload'),
    path('delete/<uuid:sound_id>/', DeleteSoundsAPIView.as_view(), name='delete-sound'),
    path('delete-tag/', DeleteSoundTagAPIView.as_view(), name='delete-sound-tag'),
    path('<uuid:id>/', SoundDetailView.as_view(), name='sound-detail'),
    path('/speaker/sample/<uuid:speaker_id>/', SpeakerSampleAudioAPIView.as_view(), name='speaker-sample'),
    path('speakers/', SpeakerListAPIView.as_view(), name='speakers-list'),
    path('speakers/add/', SpeakerCreateAPIView.as_view(), name='speaker-add'),
    path('speakers/delete/', DeleteSpeakerAPIView.as_view(), name='speaker-delete'),
    path('speakers/update/', UpdateSpeakerAPIView.as_view(), name='speaker-update'),
    path('regenerate/', RegenerateSoundAPIView.as_view(), name='regenerate'),
    path('generate/', GenerateSoundAPIView.as_view(), name='generate'),
]
