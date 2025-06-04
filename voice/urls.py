from django.urls import path
from .views import SpeakerSyncAPIView
from .views import (
    GetAllLanguagesAPIView, GetLanguagesBySpeakerAPIView,
    GetAllEmotionsAPIView, GetEmotionsBySpeakerAPIView
)

from voice.views import BindTagsToSoundAPIView, SoundListView, SoundUploadView, DeleteSoundsAPIView, DeleteSoundTagAPIView, SoundDetailView, \
    SpeakerListAPIView, RegenerateSoundAPIView, UpdateSpeakerAPIView, GenerateSoundAPIView, \
    SpeakerSampleAudioAPIView

urlpatterns = [
    path('bind-tags/', BindTagsToSoundAPIView.as_view(), name='bind-tags'),
    path('', SoundListView.as_view(), name='sound-list'),
    path('upload/', SoundUploadView.as_view(), name='sound-upload'),
    path('delete/<uuid:sound_id>/', DeleteSoundsAPIView.as_view(), name='delete-sound'),
    path('delete-tag/', DeleteSoundTagAPIView.as_view(), name='delete-sound-tag'),
    path('<uuid:id>/', SoundDetailView.as_view(), name='sound-detail'),
    path('speakers/sample/', SpeakerSampleAudioAPIView.as_view(), name='speaker-sample'),
    path('speakers/', SpeakerListAPIView.as_view(), name='speakers-list'),
    path('speakers/update/', UpdateSpeakerAPIView.as_view(), name='speaker-update'),
    path('regenerate/', RegenerateSoundAPIView.as_view(), name='regenerate'),
    path('generate/', GenerateSoundAPIView.as_view(), name='generate'),
    path('speakers/sync/', SpeakerSyncAPIView.as_view(), name='speaker-sync'),
    path('languages/', GetAllLanguagesAPIView.as_view(), name='get-all-languages'),
    path('languages/by-speaker/', GetLanguagesBySpeakerAPIView.as_view(), name='get-languages-by-speaker'),
    path('emotions/', GetAllEmotionsAPIView.as_view(), name='get-all-emotions'),
    path('emotions/by-speaker/', GetEmotionsBySpeakerAPIView.as_view(), name='get-emotions-by-speaker'),
]
