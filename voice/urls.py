from django.urls import path

from voice.views import EffectUploadView

urlpatterns = [

    path('effect/upload/', EffectUploadView.as_view(), name='effect-upload'),

]
