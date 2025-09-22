# -*- coding: utf-8 -*-
import logging
import os.path
import shutil
import uuid
import asyncio

from gradio_client import Client, handle_file
from pydub import AudioSegment
import edge_tts
from django.db import transaction
from asgiref.sync import sync_to_async
from account.models import SystemSettings
from astra.settings import TTS_PATH, SPEAKER_PATH
from voice.models import Speaker, Tts

logger = logging.getLogger("voice")


class TTSBase:
    """TTS基础接口类"""

    async def generate_speech(self, text, speaker_id, creator, video_id='', sound_id=None):
        raise NotImplementedError("子类必须实现此方法")


class IndexTTS(TTSBase):
    """IndexTTS实现"""

    async def generate_speech(self, text, speaker_id, creator, video_id='', sound_id=None):
        # 使用sync_to_async包装同步的ORM操作
        speaker = await sync_to_async(Speaker.objects.get)(id=speaker_id)
        settings = await sync_to_async(SystemSettings.objects.filter(user=creator, key='sound').first)()

        target_url = settings.value['ttsServerUrl']
        client = Client(target_url)

        # 同步的gradio客户端调用需要在线程中执行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.predict(
                emo_control_method="与音色参考音频相同",
                prompt=handle_file(os.path.join(SPEAKER_PATH, f"{speaker_id}.{speaker.spec.get('format')}")),
                text=text,
                emo_ref_path=handle_file(os.path.join(SPEAKER_PATH, f"{speaker_id}.{speaker.spec.get('format')}")),
                max_text_tokens_per_segment=120,
                api_name="/gen_single"
            )
        )

        if result.get('visible'):
            spk_path = result.get('value')
            if not sound_id:
                sound_id = str(uuid.uuid4())
            target_file = os.path.join(TTS_PATH, f'{sound_id}.wav')

            # 文件操作也需要在线程中执行
            await loop.run_in_executor(None, shutil.copy2, spk_path, target_file)
            await loop.run_in_executor(None, os.remove, spk_path)

            # 音频处理
            audio = await loop.run_in_executor(
                None,
                lambda: AudioSegment.from_file(target_file, format='wav')
            )
            duration = len(audio) / 1000.0

            # 异步保存到数据库
            tts = Tts(
                id=sound_id, format='wav', txt=text,
                speaker_id=speaker_id, video_id=video_id,
                duration=round(duration, 2), creator=creator
            )
            await sync_to_async(tts.save)()
            return tts


class EdgeTTS(TTSBase):
    """EdgeTTS实现"""

    async def generate_speech(self, text, speaker_id, creator, video_id='', sound_id=None):
        # 使用sync_to_async包装同步的ORM操作
        speaker = await sync_to_async(Speaker.objects.get)(id=speaker_id)

        if not sound_id:
            sound_id = str(uuid.uuid4())

        output_file = os.path.join(TTS_PATH, f'{sound_id}.mp3')

        # 异步生成语音
        tts = edge_tts.Communicate(
            text=text,
            voice=speaker.name,
            rate=speaker.spec.get('rate', '+0%'),
            volume=speaker.spec.get('volume', '+0%'),
            pitch=speaker.spec.get('pitch', '+0Hz')
        )
        await tts.save(output_file)

        # 音频处理在线程中执行
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: AudioSegment.from_file(output_file, format='mp3')
        )
        duration = len(audio) / 1000.0

        # 异步保存到数据库
        tts_record = Tts(
            id=sound_id,
            format='mp3',
            txt=text,
            speaker_id=speaker_id,
            video_id=video_id,
            duration=round(duration, 2),
            creator=creator
        )
        await sync_to_async(tts_record.save)()

        return tts_record


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
    async def chat_tts(text, speaker_id, creator, video_id='', sound_id=None):
        """
        异步版本的chat_tts方法
        """
        # 使用sync_to_async获取speaker信息
        speaker = await sync_to_async(Speaker.objects.get)(id=speaker_id)
        tts_service = Speech.get_tts_service(speaker.origin)
        return await tts_service.generate_speech(text, speaker_id, creator, video_id, sound_id)

    @staticmethod
    def chat_tts_sync(text, speaker_id, creator, video_id='', sound_id=None):
        """
        同步版本的chat_tts方法，供同步代码调用
        """

        async def async_wrapper():
            return await Speech.chat_tts(text, speaker_id, creator, video_id, sound_id)

        try:
            return asyncio.run(async_wrapper())
        except RuntimeError as e:
            if "event loop" in str(e):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(async_wrapper())
                finally:
                    loop.close()
            else:
                raise