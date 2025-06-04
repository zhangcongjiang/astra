import json
import logging
import os.path
import traceback
import uuid
from contextlib import closing

import requests
from pydub import AudioSegment
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from astra.settings import SOUND_PATH
from common.exceptions import BusinessException
from voice.models import Sound, Speaker

logger = logging.getLogger("voice")


class Speech:
    def __init__(self):
        # 创建带有重试机制的会话
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def chat_tts(self, text, speaker_id, sound_id=None):
        speaker = Speaker.objects.get(id=speaker_id)
        data = {
            "app_key": "",
            "audio_dl_url": "",
            "model_name": speaker.model,
            "speaker_name": speaker.name,
            "prompt_text_lang": speaker.language,
            "emotion": speaker.emotion,
            "text": text,
            "text_lang": speaker.language,
            "top_k": 10,
            "top_p": 1,
            "temperature": 1,
            "text_split_method": "按标点符号切",
            "batch_size": 1,
            "batch_threshold": 0.75,
            "split_bucket": True,
            "speed_facter": speaker.speed,
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

        try:
            # 使用with语句确保连接关闭
            with closing(self.session.post('http://127.0.0.1:8081/infer_single',
                                           headers=headers,
                                           data=json.dumps(data),
                                           timeout=30)) as res:
                result = res.json()

                if result.get('msg') == "合成成功":
                    audio_file_path = result.get('audio_url')
                    try:
                        # 使用同一个会话下载音频文件
                        with closing(self.session.get(audio_file_path.replace("0.0.0.0", "127.0.0.1"),
                                                      headers=headers,
                                                      timeout=30)) as audio_res:
                            audio_file = audio_res.content

                            if not sound_id:
                                sound_id = str(uuid.uuid4())
                            target_file = os.path.join(SOUND_PATH, f'{sound_id}.wav')

                            with open(target_file, 'wb') as f:
                                f.write(audio_file)

                            audio = AudioSegment.from_file(target_file, format='wav')
                            duration = len(audio) / 1000.0
                            spec = {
                                'duration': round(duration, 2),
                                'format': 'wav'
                            }
                            return Sound(
                                id=sound_id,
                                sound_path=f'{sound_id}.wav',
                                desc=text,
                                spec=spec,
                                category='SOUND'
                            )
                    except Exception as e:
                        logger.error(f"音频文件处理失败: {str(e)}\n{traceback.format_exc()}")
                        raise BusinessException('音频文件生成失败')
                else:
                    logger.error(f"TTS合成失败: {result.get('msg', '未知错误')}")
                    raise BusinessException(f"TTS合成失败: {result.get('msg', '未知错误')}")

        except requests.exceptions.RequestException as e:
            logger.error(f"请求TTS服务失败: {str(e)}\n{traceback.format_exc()}")
            raise BusinessException('TTS服务请求失败')
        except Exception as e:
            logger.error(f"未知错误: {str(e)}\n{traceback.format_exc()}")
            raise BusinessException('TTS处理发生未知错误')

    def __del__(self):
        # 确保会话关闭
        self.session.close()