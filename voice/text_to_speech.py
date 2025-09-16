# -*- coding: utf-8 -*-
import logging
import os.path
import shutil
import uuid

from gradio_client import Client, handle_file
from pydub import AudioSegment

from account.models import SystemSettings
from astra.settings import TTS_PATH, SPEAKER_PATH
from voice.models import Speaker, Tts

logger = logging.getLogger("voice")


class Speech:

    def chat_tts(self, text, speaker_id, creator, video_id='', sound_id=None, ):
        speaker = Speaker.objects.get(id=speaker_id)
        settings = SystemSettings.objects.filter(user=creator, key='sound').first()
        target_url = settings.value['ttsServerUrl']
        client = Client(target_url)
        result = client.predict(
            emo_control_method="与音色参考音频相同",
            prompt=handle_file(os.path.join(SPEAKER_PATH, f"{speaker_id}.{speaker.spec.get('format')}")),
            text=text,
            emo_ref_path=handle_file(os.path.join(SPEAKER_PATH, f"{speaker_id}.{speaker.spec.get('format')}")),
            max_text_tokens_per_segment=120,
            # emo_weight=0.8,
            # vec1=0,
            # vec2=0,
            # vec3=0,
            # vec4=0,
            # vec5=0,
            # vec6=0,
            # vec7=0,
            # vec8=0,
            # emo_text="",
            # emo_random=False,
            # param_16=True,
            # param_17=0.8,
            # param_18=30,
            # param_19=0.8,
            # param_20=0,
            # param_21=3,
            # param_22=10,
            # param_23=1500,
            api_name="/gen_single"
        )
        if result.get('visible'):
            spk_path = result.get('value')
            if not sound_id:
                sound_id = str(uuid.uuid4())
            target_file = os.path.join(TTS_PATH, f'{sound_id}.wav')
            shutil.copy2(spk_path, target_file)
            os.remove(spk_path)
            audio = AudioSegment.from_file(target_file, format='wav')
            duration = len(audio) / 1000.0
            tts = Tts(id=sound_id, format='wav', txt=text, speaker_id=speaker_id, video_id=video_id, duration=round(duration, 2),
                      creator=creator)
            tts.save()
            return tts
