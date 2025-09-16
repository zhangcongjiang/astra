from django.urls import path
from .views import SpeakerListPaginateAPIView

from .views import SoundPlayView

from voice.views import SoundListView, SoundUploadView, DeleteSoundsAPIView, DeleteSoundTagAPIView, SoundDetailView, \
    SpeakerListAPIView, SpeakerSelectAPIView, UpdateSpeakerAPIView, GenerateSoundAPIView, \
    SpeakerSampleAudioAPIView, SoundUpdateView, TtsListAPIView, TtsPlayAPIView, AddSpeakerView

urlpatterns = [
    path('', SoundListView.as_view(), name='sound-list'),
    path('<uuid:id>/', SoundDetailView.as_view(), name='sound-detail'),
    path('upload/', SoundUploadView.as_view(), name='sound-upload'),
    path('delete/', DeleteSoundsAPIView.as_view(), name='delete-sound'),
    path('delete-tag/', DeleteSoundTagAPIView.as_view(), name='delete-sound-tag'),

    path('speakers/add/', AddSpeakerView.as_view(), name='speaker-add'),
    path('speakers/sample/', SpeakerSampleAudioAPIView.as_view(), name='speaker-sample'),
    path('speakers/select/', SpeakerSelectAPIView.as_view(), name='speaker-select'),
    path('speakers/', SpeakerListAPIView.as_view(), name='speakers-list'),
    path('speakers/paginate/', SpeakerListPaginateAPIView.as_view(), name='speakers-paginate'),
    path('speakers/update/', UpdateSpeakerAPIView.as_view(), name='speaker-update'),
    path('generate/', GenerateSoundAPIView.as_view(), name='generate'),
    path('sound/play/', SoundPlayView.as_view(), name='sound-play'),
    path('update/', SoundUpdateView.as_view(), name='sound-update'),

    # TTS相关接口
    path('tts/', TtsListAPIView.as_view(), name='tts-list'),
    path('tts/play/', TtsPlayAPIView.as_view(), name='tts-play'),
]
