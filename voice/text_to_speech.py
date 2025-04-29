import logging
import os.path
import shutil
import traceback
import uuid

import requests
from pydub import AudioSegment

from astra.settings import SOUND_PATH
from common.exceptions import BusinessException
from voice.models import Sound

logger = logging.getLogger("voice")


class Speech:

    @staticmethod
    def chat_tts(text, voice, sound_id=None, voice_seed=None):
        data = {
            "text": text,
            "voice": voice,
        }
        if not voice_seed:
            voice_spec = {
                "prompt": "[break_6]",
                "speed": 5,
                "temperature": 0.1,
                "top_p": 0.701,
                "top_k": 20,
                "refine_max_new_token": 384,
                "infer_max_new_token": 2048,
                "text_seed": 42,
                "skip_refine": 1,
                "is_stream": 0,
                "custom_voice": 0
            }

        data.update(voice_spec)
        res = requests.post('http://127.0.0.1:9966/tts', data)
        result = res.json()
        logger.info(f"{text} -> {result}")
        if not result.get('code'):
            audio_file = result.get('audio_files', [])[0].get('filename')
            try:

                audio = AudioSegment.from_file(audio_file, format='wav')
                duration = len(audio) / 1000.0  # 将毫秒转换为秒
                spec = {
                    'duration': round(duration, 2),
                    'format': 'wav',
                    'speaker': voice,
                    'voice_sead': voice_spec
                }
                if not sound_id:
                    sound_id = str(uuid.uuid4())
                target_file = os.path.join(SOUND_PATH, f'{sound_id}.wav')
                shutil.copy(audio_file, target_file)
                return Sound(id=sound_id, sound_path=f'{sound_id}.wav', desc=text, spec=spec, category='SOUND')
            except Exception:
                logger.error(traceback.format_exc())
                raise BusinessException('音频文件生成失败')
