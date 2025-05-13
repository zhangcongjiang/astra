import logging
import os.path
import traceback
import uuid

import numpy as np
from PIL import Image
from django.utils import timezone
from moviepy import AudioFileClip
from moviepy.audio.AudioClip import concatenate_audioclips, CompositeAudioClip, AudioClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

from astra.settings import VIDEO_PATH, SOUND_PATH, NORMAL_IMG_PATH, SEED_PATH, BGM_PATH, FONTS_PATH
from video.models import Video, VideoProcess
from video.templates.video_template import VideoTemplate, InputType, VideoOrientation, MyBarLogger
from voice.text_to_speech import Speech

logger = logging.getLogger("video")


class LeftJoin(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '模板视频（1）'
        self.desc = '图片集左滑生成视频'
        self.parameters = {
            "视频模板ID": {
                "type": InputType.STRING.name,
                "key": "template_id",
            },
            "标题": {
                "type": InputType.TEXT.name,
                "key": "title",
                "max": 30,
                "min": 4
            },
            "封面图片": {
                "type": InputType.SELECT.name,
                "key": "cover_img",
                "value": "BackgroundImageList"
            },
            "默认音色": {
                "type": InputType.SELECT.name,
                "key": "speaker",
                "value": "SpeakerList"
            },
            "背景音乐": {
                "type": InputType.SELECT.name,
                "key": "bgm",
                "value": "BgmList"
            },
            "开场部分": {
                "type": InputType.OBJECT.name,
                "key": "beginning",
                "value": {
                    '文本': {
                        "type": InputType.TEXT.name,
                        "key": "text",
                        "max": 0,
                        "min": 0
                    },
                    '图片列表': {
                        "type": InputType.SELECT.name,
                        "key": "image_list",
                        "value": "NormalImageList",
                    },
                    "音色": {
                        "type": InputType.SELECT.name,
                        "key": "speaker",
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT.name,
                        "key": "effect",
                        "value": "EffectList",
                        "required": False
                    }

                }
            },
            "视频主体": {
                "type": InputType.OBJECT_LIST.name,
                "key": "content",
                "value": {
                    '文本': {
                        "type": InputType.TEXT.name,
                        "key": "text",
                        "max": 0,
                        "min": 0
                    },
                    '图片列表': {
                        "type": InputType.SELECT.name,
                        "key": "image_list",
                        "value": "NormalImageList"
                    },
                    "音色": {
                        "type": InputType.SELECT.name,
                        "key": "speaker",
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT.name,
                        "key": "effect",
                        "value": "EffectList",
                        "required": False
                    }
                }
            }
        }
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = os.path.join(VIDEO_PATH, f"{self.template_id}.mp4")
        self.default_speaker = None
        self.height, self.width = self.get_size(self.orientation)

        self.duration_start = 0

    def process(self, video_id, parameters):
        """实现带字幕和音频同步的视频生成
        
        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
        """
        logger.info(f"视频生成请求参数：{parameters}")
        param_id = self.save_parameters(parameters)
        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")
        self.redis_control.set_key(video_id, 0)
        # 获取开场部分和视频主体内容
        opening = parameters.get('beginning', {})
        contents = parameters.get('content', [])
        bgm_path = parameters.get('bgm')  # 获取背景音乐路径
        cover = parameters.get('cover_img')
        title = parameters.get('title')
        speaker = parameters.get('speaker')
        self.default_speaker = os.path.join(SEED_PATH, speaker)
        result = False
        try:
            VideoProcess(id=video_id, process='PREPARATION', start_time=timezone.now()).save()
            # 处理开场部分
            if opening:
                self._process_section(opening, "opening")
                logger.info("开场部分处理完成")

            # 处理视频主体
            for i, content in enumerate(contents):
                self._process_section(content, "content")
                logger.info("内容部分处理完成")

            # 合并所有人声音频
            final_audio = CompositeAudioClip(self.audio_clips)

            # 添加背景音乐(如果提供了)
            if bgm_path and os.path.exists(os.path.join(BGM_PATH, bgm_path)):
                bgm_clip = AudioFileClip(os.path.join(BGM_PATH, bgm_path))

                n_loops = int(final_audio.duration // bgm_clip.duration) + 1
                looped_background_music = concatenate_audioclips([bgm_clip] * n_loops)
                looped_background_music = looped_background_music.with_duration(final_audio.duration)

                bgm_clip = looped_background_music.with_volume_scaled(0.1)  # 降低音量避免盖过人声

                # 合并人声和背景音乐
                logger.info("合并音频和背景音乐")
                final_audio = CompositeAudioClip([final_audio, bgm_clip])

            # 创建合成视频
            final_clip = CompositeVideoClip(self.clips + self.subtitle_clips)
            final_clip = final_clip.with_audio(final_audio)
            final_clip = final_clip.with_duration(final_audio.duration)

            logger.info("开始生成视频文件")
            VideoProcess.objects.filter(id=video_id).update(process='PROCESS')
            final_clip.write_videofile(
                output_path,
                fps=self.frame_rate,
                preset="ultrafast",  # 平衡编码速度和质量
                threads=4,
                logger=MyBarLogger(video_id)
            )
            result = True
            logger.info(f"视频{title}生成成功")
            VideoProcess.objects.filter(id=video_id).update(process='SUCCESS')
        except Exception:
            logger.error(traceback.format_exc())
            VideoProcess.objects.filter(id=video_id).update(process='FAIL')
            os.remove(output_path)
        finally:
            Video(creator='admin', title=title, result=result, video_id=video_id, param_id=param_id).save()
            self.redis_control.delete_key(video_id)

    def _process_section(self, section_data, section_type):
        """处理单个部分(开场或内容)的视频生成"""
        text = section_data.get('text', '')
        image_paths = section_data.get('image_list', [])
        speaker = section_data.get('speaker')
        if not speaker:
            speaker = self.default_speaker
        else:
            speaker = os.path.join(SEED_PATH, speaker)
        if not text or not image_paths:
            raise ValueError(f"{section_type}缺少文本或图片列表")

        segments = self.text_utils.split_text(text)
        sg_durations = 0

        for sg in segments:
            # 生成音频
            logger.info(f"generate audio with text :{sg}")
            audio_file = os.path.join(SOUND_PATH, Speech().chat_tts(sg, voice=speaker).sound_path)
            audio_clip = AudioFileClip(audio_file)
            audio_duration = audio_clip.duration
            audio_clip = audio_clip.with_duration(audio_duration).with_start(self.duration_start)
            self.audio_clips.append(audio_clip)
            sg_durations += audio_clip.duration

            text_clip = TextClip(font=os.path.join(FONTS_PATH, 'STXINWEI.TTF'), text=sg, font_size=48, color='lightyellow',
                                 size=(self.width, 60), bg_color='black', method='caption')
            text_clip = text_clip.with_duration(audio_duration) \
                .with_start(self.duration_start) \
                .with_position(('center', self.height * 0.85)) \
                .with_opacity(0.7)
            self.subtitle_clips.append(text_clip)

            self.duration_start += audio_clip.duration

        silent_audio = AudioClip(lambda t: 0, duration=0.5)
        self.audio_clips.append(silent_audio)
        sg_durations += 0.5
        self.duration_start += 0.5

        logger.info(f"text {segments} with durations :{sg_durations}")
        # 创建图片剪辑

        # 计算每张图片的显示时间(总时长减去动画时间)
        img_count = len(image_paths)

        for i, item in enumerate(image_paths):
            clip_duration = sg_durations / img_count
            img = Image.open(os.path.join(NORMAL_IMG_PATH, item)).convert("RGB")
            width, height = img.size
            resized_height = self.height
            resized_width = int(resized_height * width / height)
            img = img.resize((self.width, self.height))
            img_clip = ImageClip(np.array(img)).with_start(self.duration_start - (img_count - i) * clip_duration).with_duration(clip_duration).with_position(('center', 'center'))
            target_x = (self.width - resized_width) / 2
            target_y = 0

            # 定义动画函数(0.25秒进入动画，停留base_duration，0.25秒退出动画)
            def pos_func(t, start_x=self.width, start_y=0, target_x=target_x, target_y=target_y, clip_duration=clip_duration):
                # 1秒进入
                if t < 0.25:
                    progress = min(t / 1, 1)
                    eased_progress = 1 - (1 - progress) ** 2  # 三次方缓出
                    x = start_x + (target_x - start_x) * eased_progress
                    y = start_y + (target_y - start_y) * eased_progress
                    return (x, y)
                # 停留
                elif t < clip_duration - 0.25:
                    return (target_x, target_y)
                # 1秒离开
                else:
                    progress = min((t - (clip_duration - 0.25)) / 1, 1)
                    eased_progress = 1 - (1 - progress) ** 2  # 三次方缓出
                    x = target_x + (-self.width - target_x) * eased_progress
                    y = target_y + (0 - target_y) * eased_progress
                    return (x, y)

            # 创建动画剪辑
            # img_clip.with_position(pos_func).with_start(self.duration_start - (img_count - i) * clip_duration)
            self.clips.append(img_clip)

    def calc_start_time(self, total_time, img_num):
        x = round(2 * (total_time - 0.2 * img_num) / (img_num * (img_num + 1)), 2)

        return [0.2 + i * x for i in range(1, img_num + 1)]
