import logging
import os
import traceback
import uuid

import pyJianYingDraft as draft
from PIL import Image
from pyJianYingDraft import trange, Font_type, Text_style, Text_intro, Keyframe_property, Clip_settings, Text_background, \
    Outro_type

from astra.settings import VIDEO_PATH
from video.models import Video
from video.templates.video_template import VideoTemplate, VideoOrientation

logger = logging.getLogger("video")


class ImagesToVideo1(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '图片集生成横版视频（1）'
        self.desc = '通过图片集生成横版视频视频，适用于比赛点评，重点新闻盘点筛选'
        self.parameters = {

        }
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = os.path.join(VIDEO_PATH, f"{self.template_id}.mp4")
        self.default_speaker = None
        self.width, self.height = self.get_size(self.orientation)
        self.duration_start = 0
        self.cover = None

    def process(self, video_id, parameters):
        """实现带字幕和音频同步的视频生成

        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
        """
        logger.info(f"视频生成请求参数：{parameters}")
        param_id = self.save_parameters(parameters)

        self.redis_control.set_key(video_id, 0)
        # 获取开场部分和视频主体内容
        start = parameters.get('start', {})
        content = parameters.get('content', [])
        # end = parameters.get('end', {})
        bgm = parameters.get('bgm')  # 获取背景音乐路径
        background = parameters.get('background')
        project_name = parameters.get('title')
        reader = parameters.get('reader')
        self.default_speaker = reader

        try:
            self.generate_draft_folder(project_name)

            script = draft.Script_file(1920, 1080)

            # 添加背景轨道（最底层）
            bg_track = script.add_track(draft.Track_type.video, track_name='背景', relative_index=0)
            bgm_track = script.add_track(draft.Track_type.audio, track_name='背景音乐', relative_index=1)

            video_track = script.add_track(draft.Track_type.video, track_name='视频', relative_index=2)

            audio_track = script.add_track(draft.Track_type.audio, track_name='配音', relative_index=3)
            captions_track = script.add_track(draft.Track_type.text, track_name='球员名字', relative_index=4)
            subtitle_track = script.add_track(draft.Track_type.text, track_name='字幕', relative_index=5)

            # 创建文本内容
            start_content = start.get('text')
            start_content_list = start_content.replace(',', '，').replace('.', '，').replace('。', '，').split('，')
            start_content_list = [item for item in start_content_list if item]

            start_time = 0.5
            logger.info(f"视频{video_id}开始处理开场部分")
            for txt in start_content_list:
                sound = self.speech.chat_tts(txt, reader)
                this_duration = sound.spec['duration']
                audio_segment = draft.Audio_segment(os.path.join(self.sound_path, sound.sound_path),
                                                    trange(f"{start_time}s", f"{this_duration}s"))
                audio_segment.add_fade("0.3s", "0.3s")
                audio_track.add_segment(audio_segment, '配音')
                caption_style = Text_style(
                    size=5,
                    bold=True,
                    color=(1, 0.75, 0.1),
                    alpha=1.0,
                    align=1,  # 左对齐
                    letter_spacing=0,
                    line_spacing=0

                )

                caption_segment = draft.Text_segment(
                    text=txt,
                    font=Font_type.文轩体,
                    timerange=trange(f"{start_time}s", f"{this_duration}s"),
                    style=caption_style,
                    clip_settings=Clip_settings(transform_x=0, transform_y=-0.9),
                    background=Text_background(
                        color="#000000",  # 黑色背景
                        alpha=0.5,  # 50%透明度
                        round_radius=0.05,  # 圆角半径
                        height=0.1,  # 背景高度
                        width=1.0  # 背景宽度
                    )
                )
                start_time += this_duration + 0.0001
                subtitle_track.add_segment(caption_segment, '字幕')

            self.redis_control.set_key(video_id, 0.2)
            logger.info(f"视频{video_id}生成进度：20%")
            start_images = start.get('images')
            img = Image.open(os.path.join(self.img_path, start_images))
            orig_width, orig_height = img.size

            # 计算缩放后的高度 (保持宽高比)
            target_width = 1920
            target_height = 1080
            # 加载图片素材
            img_material = draft.Video_material(os.path.join(self.img_path, start_images))
            scaled_height = int(orig_height * (target_width / orig_width))
            # 图片会适应性压缩
            if scaled_height > target_height:
                fit_height = 1080
                fit_width = orig_width * fit_height / orig_height

                # 创建图片片段（持续10秒）
                img_segment = draft.Video_segment(
                    img_material,
                    trange("0s", f"{start_time}s"),
                    clip_settings=Clip_settings(scale_x=target_width / fit_width, scale_y=scaled_height / fit_height)

                )

                img_segment.add_keyframe(Keyframe_property.position_x, "0s", 0)
                img_segment.add_keyframe(Keyframe_property.position_y, "0s", round(1 - scaled_height / fit_height, 4))

                img_segment.add_keyframe(Keyframe_property.position_x, "1s", 0)
                img_segment.add_keyframe(Keyframe_property.position_y, "1s", round(1 - scaled_height / fit_height, 4))

                img_segment.add_keyframe(Keyframe_property.position_x, f"{start_time - 1}s", 0)
                img_segment.add_keyframe(Keyframe_property.position_y, f"{start_time - 1}s", round(scaled_height / fit_height - 1, 4))

                img_segment.add_keyframe(Keyframe_property.position_x, f"{start_time}s", 0)
                img_segment.add_keyframe(Keyframe_property.position_y, f"{start_time}s", round(scaled_height / fit_height - 1, 4))
            else:

                # 创建图片片段（持续10秒）
                img_segment = draft.Video_segment(
                    img_material,
                    trange("0s", f"{start_time}s"),

                )

            video_track.add_segment(img_segment, '视频')

            content_time = start_time

            for i, item in enumerate(content):
                images = item.get('images')
                name = item.get('name')
                text = item.get('text')

                section_time = 0
                section_start_time = content_time
                for txt in text.split('，'):
                    sound = self.speech.chat_tts(txt, reader)
                    this_duration = sound.spec['duration']
                    subtitle_start = content_time
                    section_time += this_duration
                    content_time += this_duration + 0.0001
                    audio_segment = draft.Audio_segment(os.path.join(self.sound_path, sound.sound_path),
                                                        trange(f"{subtitle_start}s", f"{this_duration}s"))
                    audio_segment.add_fade("0.3s", "0.3s")
                    audio_track.add_segment(audio_segment, '配音')

                    caption_style = Text_style(
                        size=5,
                        bold=True,
                        color=(1, 0.75, 0.1),
                        alpha=1.0,
                        align=1,  # 左对齐
                        letter_spacing=0,
                        line_spacing=0

                    )

                    caption_segment = draft.Text_segment(
                        text=txt,
                        font=Font_type.文轩体,
                        timerange=trange(f"{subtitle_start}s", f"{this_duration}s"),
                        style=caption_style,
                        clip_settings=Clip_settings(transform_x=0, transform_y=-0.9),
                        background=Text_background(
                            color="#000000",  # 黑色背景
                            alpha=0.5,  # 50%透明度
                            round_radius=0.05,  # 圆角半径
                            height=0.1,  # 背景高度
                            width=1.0  # 背景宽度
                        )
                    )
                    subtitle_start += round(5 / len(text.split('，')), 4) + 0.0001
                    subtitle_track.add_segment(caption_segment, '字幕')

                caption_style = Text_style(
                    size=5,
                    bold=True,
                    color=(1, 0.75, 0.1),
                    alpha=1.0,
                    align=1,  # 左对齐
                    letter_spacing=0,
                    line_spacing=0

                )

                caption_segment = draft.Text_segment(
                    text=name,
                    font=Font_type.文轩体,
                    timerange=trange(f"{section_start_time + 0.2}s", f"{section_time - 0.5}s"),
                    style=caption_style,
                    clip_settings=Clip_settings(transform_x=-0.5, transform_y=0.9),

                )
                caption_segment.add_animation(Text_intro.居中打字, duration=300000)

                captions_track.add_segment(caption_segment, '球员名字')

                for image in images:
                    img_material = draft.Video_material(os.path.join(self.img_path, image))
                    img_segment = draft.Video_segment(
                        img_material,
                        trange(f"{section_start_time}s", f"{round(section_time / len(images), 4)}s")
                    )
                    img_segment.add_animation(Outro_type.轻微放大, duration=200000)
                    video_track.add_segment(img_segment, '视频')
                    section_start_time += round(section_time / len(images), 4) + 0.0001

                self.redis_control.set_key(video_id, round(0.2 + (i + 1) * 0.8 / len(content), 2))
                logger.info(f"视频{video_id}生成进度：{round(0.2 + (i + 1) * 0.7 / len(content), 2) * 100}%")

            # 最后收尾用0.5s
            content_time += 0.5
            bg_material = draft.Video_material(os.path.join(self.img_path, background))
            bg_segment = draft.Video_segment(
                bg_material,
                trange("0s", f"{content_time}s")
            )
            bg_track.add_segment(bg_segment, '背景')

            # 添加背景音乐（持续整个视频时长10秒）
            bgm_sound = draft.Audio_material(os.path.join(self.bgm_path, bgm))  # 背景音乐文件
            bgm_duration = bgm_sound.duration

            if content_time > bgm_duration:
                loop_time = 0
                while content_time > bgm_duration:
                    bgm_segment = draft.Audio_segment(
                        bgm_sound,
                        trange(f"{loop_time * bgm_duration}s", f"{bgm_duration}s"),
                        volume=0.1
                    )
                    bgm_segment.add_fade("1s", "1s")
                    bgm_track.add_segment(bgm_segment, '背景音乐')
                    content_time -= bgm_duration
                    loop_time += 1
            else:
                bgm_segment = draft.Audio_segment(
                    bgm_sound,
                    trange("0s", f"{content_time}s"),  #
                    volume=0.1
                )
                bgm_segment.add_fade("1s", "0s")
                bgm_track.add_segment(bgm_segment, '背景音乐')
            # 保存草稿
            draft_content_path = os.path.join(self.draft_folder, project_name, 'draft_content.json')
            script.dump(draft_content_path)
            logger.info(f"视频{video_id}生成进度：100%")
            logger.info(f"草稿 '{project_name}' 已成功生成！")
            Video(creator='admin', title=project_name, result=True, id=video_id, param_id=param_id).save()
        except Exception as e:
            logger.error(traceback.format_exc())
            Video(creator='admin', title=project_name, result=False, id=video_id, param_id=param_id).save()
            raise e
