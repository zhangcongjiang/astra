# -*- coding: utf-8 -*-
import logging
import os.path
import shutil
import uuid

from gradio_client import Client, handle_file
from pydub import AudioSegment
import edge_tts
import asyncio
import os
import uuid

from account.models import SystemSettings
from astra.settings import TTS_PATH, SPEAKER_PATH
from voice.models import Speaker, Tts

logger = logging.getLogger("voice")


class TTSBase:
    """TTS基础接口类（同步版本）"""

    def generate_speech(self, text, speaker_id, creator, video_id='', sound_id=None):
        raise NotImplementedError("子类必须实现此方法")


class IndexTTS(TTSBase):
    """IndexTTS实现（同步）"""

    def generate_speech(self, text, speaker_id, creator, video_id='', sound_id=None):
        # 同步执行数据库与文件操作
        speaker = Speaker.objects.get(id=speaker_id)
        settings = SystemSettings.objects.filter(user=creator, key='sound').first()

        target_url = settings.value['ttsServerUrl'] if settings and settings.value else None
        if not target_url:
            raise ValueError("未配置ttsServerUrl")

        client = Client(target_url)
        result = client.predict(
            emo_control_method="与音色参考音频相同",
            prompt=handle_file(os.path.join(SPEAKER_PATH, f"{speaker_id}.{speaker.spec.get('format')}")),
            text=text,
            emo_ref_path=handle_file(os.path.join(SPEAKER_PATH, f"{speaker_id}.{speaker.spec.get('format')}")),
            max_text_tokens_per_segment=120,
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

            # 同步保存到数据库
            tts = Tts(
                id=sound_id, format='wav', txt=text,
                speaker_id=speaker_id, video_id=video_id,
                duration=round(duration, 3), creator=creator
            )
            tts.save()
            return tts
        else:
            raise ValueError("TTS生成失败")


class EdgeTTS(TTSBase):
    """Edge TTS实现（同步）"""

    def generate_speech(self, text, speaker_id, creator, video_id='', sound_id=None):
        speaker = Speaker.objects.get(id=speaker_id)
        # 语音名称优先取spec.voice，其次使用speaker.name
        voice_name = (speaker.spec or {}).get('voice') or speaker.name
        if not voice_name:
            raise ValueError("EdgeTTS需要提供语音名称(voice)，请在Speaker.spec.voice或name中设置")

        # 速度/音量/音调可从spec中覆盖，默认参考示例代码
        rate = (speaker.spec or {}).get('rate', '+10%')
        volume = (speaker.spec or {}).get('volume', '+20%')
        pitch = (speaker.spec or {}).get('pitch', '+10Hz')

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_name,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )

            if not sound_id:
                sound_id = str(uuid.uuid4())

            target_file = os.path.join(TTS_PATH, f'{sound_id}.mp3')


            asyncio.run(communicate.save(target_file))

            audio = AudioSegment.from_file(target_file, format='mp3')
            duration = len(audio) / 1000.0

            # 保存到数据库
            tts = Tts(
                id=sound_id, format='mp3', txt=text,
                speaker_id=speaker_id, video_id=video_id,
                duration=round(duration, 3), creator=creator
            )
            tts.save()
            return tts
        except Exception as e:
            logger.exception("EdgeTTS生成失败: %s", e)
            raise ValueError(f"EdgeTTS生成失败: {e}")


class Speech:
    """TTS工厂类"""

    @staticmethod
    def get_tts_service(speaker_origin):
        """
        根据speaker的origin获取对应的TTS服务
        """
        if speaker_origin == 'INDEX_TTS':
            return IndexTTS()
        elif speaker_origin == 'EDGE_TTS':
            return EdgeTTS()
        else:
            raise ValueError(f"不支持的TTS类型: {speaker_origin}")

    @staticmethod
    def chat_tts(text, speaker_id, creator, video_id='', sound_id=None):
        """
        同步版本的chat_tts方法，供同步代码调用
        """
        # 直接调用同步实现
        speaker = Speaker.objects.get(id=speaker_id)
        tts_service = Speech.get_tts_service(speaker.origin)
        return tts_service.generate_speech(text, speaker_id, creator, video_id, sound_id)
