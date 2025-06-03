import json
import logging
import traceback
import uuid

import requests
from pydub import AudioSegment

from common.exceptions import BusinessException
from voice.models import Sound

logger = logging.getLogger("voice")


class Speech:

    def chat_tts(self, text, model, speaker, sound_id=None):
        data = {
            "app_key": "",
            "audio_dl_url": "",
            "model_name": model,
            "speaker_name": speaker,
            "prompt_text_lang": "中文",
            "emotion": "中立_neutral",
            "text": text,
            "text_lang": "中文",
            "top_k": 10,
            "top_p": 1,
            "temperature": 1,
            "text_split_method": "按标点符号切",
            "batch_size": 1,
            "batch_threshold": 0.75,
            "split_bucket": True,
            "speed_facter": 1,
            "fragment_interval": 0.3,
            "media_type": "wav",
            "parallel_infer": True,
            "repetition_penalty": 1.35,
            "seed": -1
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        res = requests.post('http://127.0.0.1:8081/infer_single', headers=headers, data=json.dumps(data))
        result = res.json()

        if result.get('msg') == "合成成功":
            audio_file_path = result.get('audio_url')
            try:
                audio_file = requests.get(audio_file_path.replace("0.0.0.0", "127.0.0.1"), headers=headers).content
                if not sound_id:
                    sound_id = str(uuid.uuid4())
                target_file = f'{sound_id}.wav'
                with open(target_file, 'wb') as f:  # 'wb' 表示二进制写入
                    f.write(audio_file)
                audio = AudioSegment.from_file(target_file, format='wav')
                duration = len(audio) / 1000.0  # 将毫秒转换为秒
                spec = {
                    'duration': round(duration, 2),
                    'format': 'wav'
                }
                return Sound(id=sound_id, sound_path=f'{sound_id}.wav', desc=text, spec=spec, category='SOUND')
            except Exception:
                logger.error(traceback.format_exc())
                raise BusinessException('音频文件生成失败')
