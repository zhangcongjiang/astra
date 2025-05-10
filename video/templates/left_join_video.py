import logging
import os.path
import uuid

from astra.settings import VIDEO_PATH
from video.templates.video_template import VideoTemplate, InputType, VideoOrientation
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.video.VideoClip import TextClip
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
                "type": InputType.STRING,
                "key": "template_id",
            },
            "标题": {
                "type": InputType.TEXT,
                "key": "title",
                "max": 30,
                "min": 4
            },
            "封面图片": {
                "type": InputType.SELECT,
                "key": "cover_img",
                "value": "BackgroundImageList"
            },
            "默认音色": {
                "type": InputType.SELECT,
                "key": "speaker",
                "value": "SpeakerList"
            },
            "背景音乐": {
                "type": InputType.SELECT,
                "key": "bgm",
                "value": "BgmList"
            },
            "开场部分": {
                "type": InputType.OBJECT,
                "key": "opening",
                "value": {
                    '文本': {
                        "type": InputType.TEXT,
                        "key": "text",
                        "max": 0,
                        "min": 0
                    },
                    '图片列表': {
                        "type": InputType.SELECT,
                        "key": "image_list",
                        "value": "NormalImageList",
                    },
                    "音色": {
                        "type": InputType.SELECT,
                        "key": "speaker",
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT,
                        "key": "effect",
                        "value": "EffectList",
                        "required": False
                    }

                }
            },
            "视频主体": {
                "type": InputType.OBJECT_LIST,
                "key": "content",
                "value": {
                    '文本': {
                        "type": InputType.TEXT,
                        "key": "text",
                        "max": 0,
                        "min": 0
                    },
                    '图片列表': {
                        "type": InputType.SELECT,
                        "key": "image_list",
                        "value": "NormalImageList"
                    },
                    "音色": {
                        "type": InputType.SELECT,
                        "key": "speaker",
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT,
                        "key": "effect",
                        "value": "EffectList",
                        "required": False
                    }
                }
            }
        }
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = os.path.join(VIDEO_PATH, f"{self.template_id}.mp4")

    def process(self, video_id, parameters):
        """实现带字幕和音频同步的视频生成
        
        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
        """
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.audio.AudioClip import CompositeAudioClip

        # 获取开场部分和视频主体内容
        opening = parameters.get('opening', {})
        contents = parameters.get('content', [])
        bgm_path = parameters.get('bgm')  # 获取背景音乐路径

        # 视频参数
        fps = 24
        clips = []
        audio_clips = []

        # 处理开场部分
        if opening:
            opening_clip, opening_audio = self._process_section(opening, "opening")
            clips.append(opening_clip)
            audio_clips.append(opening_audio)

        # 处理视频主体
        for content in contents:
            content_clip, content_audio = self._process_section(content, "content")
            clips.append(content_clip)
            audio_clips.append(content_audio)

        # 合并所有人声音频
        final_audio = CompositeAudioClip(audio_clips)

        # 添加背景音乐(如果提供了)
        if bgm_path and os.path.exists(bgm_path):
            bgm_clip = AudioFileClip(bgm_path)
            
            # 循环背景音乐以匹配视频时长
            if bgm_clip.duration < final_audio.duration:
                loop_count = int(final_audio.duration / bgm_clip.duration) + 1
                bgm_clip = bgm_clip.loop(n=loop_count)
            
            bgm_clip = bgm_clip.with_duration(final_audio.duration)
            bgm_clip = bgm_clip.with_volumex(0.3)  # 降低音量避免盖过人声
            
            # 合并人声和背景音乐
            final_audio = CompositeAudioClip([final_audio, bgm_clip])

        # 创建合成视频
        final_clip = CompositeVideoClip(clips)
        final_clip = final_clip.with_audio(final_audio)

        # 输出视频文件
        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")
        final_clip.write_videofile(output_path, fps=fps, threads=4)

        return output_path

    def _process_section(self, section_data, video_id, section_type):
        """处理单个部分(开场或内容)的视频生成"""
        text = section_data.get('text', '')
        image_paths = section_data.get('image_list', [])
        speaker = section_data.get('speaker')
        screen_width, screen_height = 1920, 1080
        if not text or not image_paths:
            raise ValueError(f"{section_type}缺少文本或图片列表")

        # 生成音频
        audio_data = Speech().chat_tts(text, voice=speaker)
        audio_clip = AudioArrayClip(audio_data, fps=44100)
        audio_duration = audio_clip.duration

        # 计算每张图片的显示时间(总时长减去动画时间)
        img_count = len(image_paths)
        animation_duration = 0.25  # 进入和退出各0.25秒
        base_duration = (audio_duration - (img_count * animation_duration)) / img_count

        # 创建图片剪辑
        img_clips = []
        for i, img_path in enumerate(image_paths):
            # 每张图片总时长 = 基础时长 + 动画时间
            img_total_duration = base_duration + animation_duration
            img_clip = ImageClip(img_path)
            img_clip = img_clip.with_duration(img_total_duration)
            img_clip = img_clip.with_effects([('resize', {'height': screen_height * 0.8})])

            # 计算图片宽度和位置
            img_width = img_clip.w
            start_pos = (screen_width, (screen_height - img_clip.h) / 2)  # 从右侧进入
            end_pos = ((screen_width - img_width) / 2, (screen_height - img_clip.h) / 2)  # 中央位置

            # 定义动画函数(0.25秒进入动画，停留base_duration，0.25秒退出动画)
            def make_frame(t):
                if t < 0.25:  # 进入动画
                    x = start_pos[0] + (end_pos[0] - start_pos[0]) * (t / 0.25)
                    return img_clip.get_frame(t).set_position((x, end_pos[1]))
                elif t < (0.25 + base_duration):  # 停留
                    return img_clip.get_frame(t).set_position(end_pos)
                else:  # 退出动画
                    x = end_pos[0] + (start_pos[0] - end_pos[0]) * ((t - (0.25 + base_duration)) / 0.25)
                    return img_clip.get_frame(t).set_position((x, end_pos[1]))

            # 创建动画剪辑
            animated_clip = img_clip.fl(lambda gf, t: make_frame(t), apply_to=['mask'])

            # 设置剪辑的开始时间(上一张开始退出时下一张开始进入)
            start_time = i * (base_duration + animation_duration - 0.25)
            animated_clip = animated_clip.with_start(start_time)

            img_clips.append(animated_clip)

        # 创建字幕
        text_clip = TextClip(
            text,
            fontsize=40,
            color='white',
            bg_color='transparent',
            size=(screen_width * 0.8, None)
        )
        text_clip = text_clip.with_duration(audio_duration)
        text_clip = text_clip.with_position(('center', screen_height * 0.85))

        # 合成视频部分
        section_clip = CompositeVideoClip(img_clips + [text_clip])
        section_clip = section_clip.with_audio(audio_clip)

        return section_clip

    def calc_start_time(self, total_time, img_num):
        x = round(2 * (total_time - 0.2 * img_num) / (img_num * (img_num + 1)), 2)

        return [0.2 + i * x for i in range(1, img_num + 1)]
