from django.urls import path
from .views import SpeakerSyncAPIView
from .views import (
    GetAllLanguagesAPIView, GetLanguagesBySpeakerAPIView,
    GetAllEmotionsAPIView, GetEmotionsBySpeakerAPIView
)
from .views import SoundPlayView

from voice.views import  SoundListView, SoundUploadView, DeleteSoundsAPIView, DeleteSoundTagAPIView, SoundDetailView, \
    SpeakerListAPIView, SpeakerSelectAPIView, UpdateSpeakerAPIView, GenerateSoundAPIView, \
    SpeakerSampleAudioAPIView, SoundUpdateView, TtsListAPIView, TtsPlayAPIView

urlpatterns = [
    path('', SoundListView.as_view(), name='sound-list'),
    path('upload/', SoundUploadView.as_view(), name='sound-upload'),
    path('delete/', DeleteSoundsAPIView.as_view(), name='delete-sound'),
    path('delete-tag/', DeleteSoundTagAPIView.as_view(), name='delete-sound-tag'),
    path('<uuid:id>/', SoundDetailView.as_view(), name='sound-detail'),
    path('speakers/sample/', SpeakerSampleAudioAPIView.as_view(), name='speaker-sample'),
    path('speakers/select/', SpeakerSelectAPIView.as_view(), name='speaker-select'),
    path('speakers/', SpeakerListAPIView.as_view(), name='speakers-list'),
    path('speakers/update/', UpdateSpeakerAPIView.as_view(), name='speaker-update'),
    path('generate/', GenerateSoundAPIView.as_view(), name='generate'),
    path('speakers/sync/', SpeakerSyncAPIView.as_view(), name='speaker-sync'),
    path('languages/', GetAllLanguagesAPIView.as_view(), name='get-all-languages'),
    path('languages/by-speaker/', GetLanguagesBySpeakerAPIView.as_view(), name='get-languages-by-speaker'),
    path('emotions/', GetAllEmotionsAPIView.as_view(), name='get-all-emotions'),
    path('emotions/by-speaker/', GetEmotionsBySpeakerAPIView.as_view(), name='get-emotions-by-speaker'),
    path('sound/play/', SoundPlayView.as_view(), name='sound-play'),
    path('update/', SoundUpdateView.as_view(), name='sound-update'),
    
    # TTS相关接口
    path('tts/', TtsListAPIView.as_view(), name='tts-list'),
    path('tts/play/', TtsPlayAPIView.as_view(), name='tts-play'),
]
