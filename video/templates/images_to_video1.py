import logging
import os
import traceback
import uuid
import json

import pyJianYingDraft as draft
from PIL import Image as PilImage
from image.models import Image
from pyJianYingDraft import trange, Font_type, Text_style, Text_intro, Keyframe_property, Clip_settings, Text_background, \
    Outro_type

from astra.settings import VIDEO_PATH
from video.models import Video
from video.templates.video_template import VideoTemplate, VideoOrientation
from voice.models import Sound

logger = logging.getLogger("video")


class ImagesToVideo1(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '图片集生成横版视频（1）'
        self.desc = '通过图片集生成横版视频视频，适用于比赛点评，重点新闻盘点筛选'
        self.parameters = {
            'form': [{
                'name': 'background',
                'label': '背景图片',
                'type': 'select',
                'required': True,
                'options': {
                    'source': 'server',
                    'resourceType': 'image'
                },
                'description': '从您的媒体库中选择一张背景图片。'
            },
                {
                    'name': 'bgm',
                    'label': '背景音乐',
                    'type': 'select',
                    'required': True,
                    'options': {
                        'source': 'server',
                        'resourceType': 'audio'
                    },
                    'description': '从您的媒体库中选择一首背景音乐。'
                },
                {
                    'name': 'title',
                    'label': '视频标题',
                    'type': 'input',
                    'inputType': 'text',
                    'required': True,
                    'placeholder': '请输入视频的标题'
                },
                {
                    'name': 'reader',
                    'label': '选择配音员',
                    'type': 'select',
                    'required': False,
                    'options': {
                        'source': 'remote',
                        'url': '/voice/speakers/select/',
                        'valueKey': 'id',
                        'labelKey': 'name'
                    },
                    'description': '选择一个AI配音员来朗读文案。'
                },
                {
                    'name': 'start_images',
                    'label': '开场图片',
                    'type': 'select',
                    'required': True,
                    'options': {
                        'source': 'server',
                        'resourceType': 'image'
                    }
                },
                {
                    'name': 'start_text',
                    'label': '开场文案',
                    'type': 'textarea',
                    'rows': 3,
                    'required': True,
                    'placeholder': '请输入视频的开场白。'
                },
                {
                    'name': 'content',
                    'label': '核心内容场景',
                    'type': 'group',
                    'replicable': True,
                    'description': '点击“添加场景”以创建多个视频片段。',
                    'fields': [{
                        'name': 'images',
                        'label': '场景关联图片',
                        'type': 'select',
                        'multiple': True,
                        'required': True,
                        'options': {
                            'source': 'server',
                            'resourceType': 'image'
                        },
                        'description': '按住Ctrl/Command可选择多张图片。'
                    },
                        {
                            'name': 'name',
                            'label': '场景核心人物/事件',
                            'type': 'input',
                            'inputType': 'text',
                            'placeholder': '例如：布朗尼·詹姆斯'
                        },
                        {
                            'name': 'text',
                            'label': '场景解说文案',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入该场景的解说词。'
                        }
                    ]
                }
            ]
        }
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = os.path.join(VIDEO_PATH, "iamges_to_video1.mp4")
        self.default_speaker = None
        self.width, self.height = self.get_size(self.orientation)
        self.duration_start = 0
        self.cover = None
        self.video_type = 'JianYing'

    def process(self, user, video_id, parameters):
        """实现带字幕和音频同步的视频生成

        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
            :param user: 创建者
        """
        import time
        start_time = time.time()  # 记录开始时间
        
        logger.info(f"视频生成请求参数：{parameters}")
        project_name = parameters.get('title')
        param_id = self.save_parameters(self.template_id, user, project_name, parameters)

        # 获取开场部分和视频主体内容
        content = parameters.get('content', [])
        # end = parameters.get('end', {})
        bgm = parameters.get('bgm')  # 获取背景音乐路径
        background = parameters.get('background')
        background_img = Image.objects.get(id=background)

        reader = parameters.get('reader')
        self.default_speaker = reader
        Video(creator=user, title=project_name, video_type=self.video_type, result='Process', process=0.0, id=video_id, param_id=param_id).save()
        try:
            draft_folder = self.get_draft_folder(user)
            self.generate_draft(draft_folder, project_name)

            script = draft.Script_file(1920, 1080)

            # 添加背景轨道（最底层）
            bg_track = script.add_track(draft.Track_type.video, track_name='背景', relative_index=0)
            bgm_track = script.add_track(draft.Track_type.audio, track_name='背景音乐', relative_index=1)

            video_track = script.add_track(draft.Track_type.video, track_name='视频', relative_index=2)

            audio_track = script.add_track(draft.Track_type.audio, track_name='配音', relative_index=3)
            captions_track = script.add_track(draft.Track_type.text, track_name='球员名字', relative_index=4)
            subtitle_track = script.add_track(draft.Track_type.text, track_name='字幕', relative_index=5)

            # 创建文本内容
            start_content = parameters.get('start_text')
            start_content_list = start_content.replace(',', '，').replace('.', '，').replace('。', '，').split('，')
            start_content_list = [item for item in start_content_list if item]

            start_time = 0.5
            logger.info(f"视频{video_id}开始处理开场部分")
            for txt in start_content_list:
                tts = self.speech.chat_tts(txt, reader, user, video_id)
                this_duration = tts.duration
                audio_segment = draft.Audio_segment(os.path.join(self.sound_path, f"{tts.id}.{tts.format}"),
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

            Video.objects.filter(id=video_id).update(process=0.2)
            logger.info(f"视频{video_id}生成进度：20%")
            start_images = parameters.get('start_images')
            img_obj = Image.objects.get(id=start_images)
            img = PilImage.open(os.path.join(self.img_path, img_obj.img_name))
            orig_width, orig_height = img.size

            # 计算缩放后的高度 (保持宽高比)
            target_width = 1920
            target_height = 1080
            # 加载图片素材
            img_material = draft.Video_material(os.path.join(self.img_path, img_obj.img_name))
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

                text = item.get('text')

                section_time = 0
                section_start_time = content_time
                for txt in text.split('，'):
                    tts = self.speech.chat_tts(txt, reader, user, video_id)
                    this_duration = tts.duration
                    subtitle_start = content_time
                    section_time += this_duration
                    content_time += this_duration + 0.0001
                    audio_segment = draft.Audio_segment(os.path.join(self.tts_path, f"{tts.id}.{tts.format}"),
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
                name = item.get('name')
                if name:
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
                    img_obj = Image.objects.get(id=image)
                    img_material = draft.Video_material(os.path.join(self.img_path, img_obj.img_name))
                    img_segment = draft.Video_segment(
                        img_material,
                        trange(f"{section_start_time}s", f"{round(section_time / len(images), 4)}s")
                    )
                    img_segment.add_animation(Outro_type.轻微放大, duration=200000)
                    video_track.add_segment(img_segment, '视频')
                    section_start_time += round(section_time / len(images), 4) + 0.0001

                Video.objects.filter(id=video_id).update(process=round(0.2 + (i + 1) * 0.8 / len(content), 3))
                logger.info(f"视频{video_id}生成进度：{round(0.2 + (i + 1) * 0.7 / len(content), 3) * 100}%")

            # 最后收尾用0.5s
            content_time += 0.5
            bg_material = draft.Video_material(os.path.join(self.img_path, background_img.img_name))
            bg_segment = draft.Video_segment(
                bg_material,
                trange("0s", f"{content_time}s")
            )
            bg_track.add_segment(bg_segment, '背景')
            bgm_obj = Sound.objects.get(id=bgm)

            # 添加背景音乐（持续整个视频时长10秒）
            bgm_sound = draft.Audio_material(os.path.join(self.sound_path, bgm_obj.sound_path))  # 背景音乐文件
            bgm_duration = round(bgm_sound.duration / 1000000, 4)
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

            bgm_segment = draft.Audio_segment(
                bgm_sound,
                trange(f"{loop_time * bgm_duration}s", f"{content_time}s"),  #
                volume=0.1
            )
            bgm_segment.add_fade("1s", "1s")
            bgm_track.add_segment(bgm_segment, '背景音乐')
            # 保存草稿
            draft_content_path = os.path.join(draft_folder, project_name, 'draft_content.json')
            script.dump(draft_content_path)
            logger.info(f"视频{video_id}生成进度：100%")
            logger.info(f"草稿 '{project_name}' 已成功生成！")
            Video.objects.filter(id=video_id).update(result='Success', process=1.0, cost=time.time() - start_time)
        except Exception as e:
            logger.error(traceback.format_exc())
            Video.objects.filter(id=video_id).update(result='Fail')
            raise e
