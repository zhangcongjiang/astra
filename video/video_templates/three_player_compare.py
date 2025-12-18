import logging
import os
import shutil
import textwrap
import time
import traceback
import uuid

import numpy as np
from PIL import Image as PilImage, ImageDraw, ImageFont, ImageEnhance
from moviepy import *
from moviepy.audio.fx import AudioFadeOut
from moviepy.video.fx import CrossFadeIn, FadeIn, SlideIn
from pydub import AudioSegment

from astra.settings import VIDEO_PATH, IMG_PATH, TMP_PATH
from image.models import Image
from video.models import Video
from video.video_templates.video_template import VideoTemplate, VideoOrientation
from voice.models import Sound

logger = logging.getLogger("video")


class ThreePlayerCompare(VideoTemplate):
    """竖版：球员列表视频模板（重新设计开场与卡片，单人逐段展示）"""

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '三个球员进行对比（竖版）'
        self.desc = '竖版视频：三个球员数据对比'
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
                    'fields': [
                        {
                            'name': 'image_path',
                            'label': '球员全身照',
                            'type': 'select',
                            'multiple': False,
                            'required': True,
                            'options': {
                                'source': 'server',
                                'resourceType': 'image'
                            }
                        },
                        {
                            'name': 'name',
                            'label': '球员姓名',
                            'type': 'input',
                            'inputType': 'text',
                            'required': True,
                            'placeholder': '例如：勒布朗·詹姆斯'
                        },
                        {
                            'name': 'key_note',
                            'label': '关键信息',
                            'type': 'input',
                            'inputType': 'text',
                            'required': True,
                            'placeholder': '例如：2003年状元秀'
                        },
                        {
                            'name': 'stats',
                            'label': '球员数据',
                            'type': 'input',
                            'inputType': 'text',
                            'required': True,
                            'placeholder': '例如：30.2分5.5篮板6.3助攻1.4抢断0.2盖帽'
                        },
                        {
                            'name': 'accuracy',
                            'label': '命中率',
                            'type': 'input',
                            'inputType': 'text',
                            'required': True,
                            'placeholder': '例如：命中率：47.9% | 42.3% | 91.5%'
                        }
                    ]
                }
            ]
        }
        self.orientation = VideoOrientation.VERTICAL.name
        self.width, self.height = self.get_size(self.orientation)  # 900x1600
        self.demo = "/media/videos/player_compare.mp4"
        self.default_speaker = None
        self.video_type = 'Regular'
        self.tmps = None

    def process(self, user, video_id, parameters):
        """竖版实现：自定义开场、单卡片逐段展示，不与横版并行展示。
        Args:
            user: 创建者
            video_id: 视频唯一ID
            parameters: 参数集合
        """
        begin = time.time()
        self.tmps = os.path.join(TMP_PATH, video_id)
        if not os.path.exists(self.tmps):
            os.mkdir(self.tmps)
        logger.info(f"竖版视频生成参数：{parameters}")

        project_name = parameters.get('title')
        param_id = self.save_parameters(self.template_id, user, project_name, parameters)
        start_text = parameters.get('start_text', '')

        bgm = parameters.get('bgm')
        bgm_sound = Sound.objects.get(id=bgm)
        bgm_path = os.path.join(self.sound_path, bgm_sound.sound_path)

        content = parameters.get('content') or []
        reader = parameters.get('reader')

        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")
        Video(creator=user, title=project_name, content=start_text, video_type=self.video_type,
              result='Process', process=0.0, id=video_id, param_id=param_id).save()

        try:
            # 背景
            bkg = parameters.get('background')
            if bkg:
                bkg_img = Image.objects.get(id=bkg)
                bkg_path = os.path.join(self.img_path, bkg_img.img_name)
                bg_img_path = self.prepare_background(bkg_path, target_size=(self.width, self.height), brightness_factor=0.1)
            else:
                image = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 255))
                bg_img_path = os.path.join(self.tmps, "tmp_bg.png")
                image.save(bg_img_path)

            start = 0.5
            final_audio = AudioSegment.silent(duration=0)

            # 开场语音与字幕
            start_segments = self.text_utils.split_text(start_text)
            for i, sg in enumerate(start_segments):
                tts = self.speech.chat_tts(sg, reader, user, video_id)
                tts_path = os.path.join(self.tts_path, f'{tts.id}.{tts.format}')
                if not os.path.isfile(tts_path):
                    fallback_exts = ['mp3', 'wav'] if tts.format != 'mp3' else ['wav']
                    for ext in fallback_exts:
                        alt = os.path.join(self.tts_path, f'{tts.id}.{ext}')
                        if os.path.isfile(alt):
                            tts_path = alt
                            break
                try:
                    try:
                        audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                    except Exception:
                        try:
                            audio = AudioSegment.from_file(tts_path, format='mp3').fade_in(200).fade_out(200)
                        except Exception:
                            audio = AudioSegment.from_file(tts_path, format='wav').fade_in(200).fade_out(200)
                except Exception:
                    try:
                        audio = AudioSegment.from_file(tts_path, format='mp3').fade_in(200).fade_out(200)
                    except Exception:
                        audio = AudioSegment.from_file(tts_path, format='wav').fade_in(200).fade_out(200)

                if i == 0:
                    final_audio = audio
                    start += tts.duration
                else:
                    final_audio = final_audio.append(audio, crossfade=200)
                    start += tts.duration - 0.2

            final_audio = final_audio.append(AudioSegment.silent(duration=500))
            start += 0.5
            total_durations = start + 3

            vertical_cover = self.generate_vertical_cover(project_name, content[0].get('image_path'), user)
            Video.objects.filter(id=video_id).update(vertical_cover=vertical_cover, process=0.2)

            horizontal_cover = self.generate_horizontal_cover(project_name, [info.get('image_path') for info in content], user)
            Video.objects.filter(id=video_id).update(cover=horizontal_cover)

            clips = []
            start_times = [0.5, 1.5, 2.5]  # 飞入开始时间
            text_times = [1, 2, 3]  # 文本出现时间

            for idx, info in enumerate(content):
                img = self.img_utils.trim_image(info.get('image_path'))
                img_w, img_h = img.size
                name = info.get('name')
                key_note = info.get('key_note')
                stats = info.get('stats')
                accuracy = info.get('accuracy')
                text_data = [name, key_note, stats, accuracy]
                if idx % 2 == 0:
                    final_x = self.width - 30 - img_w
                else:
                    final_x = 30
                final_y = (idx + 1) * 400 - img_h // 2
                # === 使用你提供的飞入动画 ===
                img_clip = self.create_deal_animation(
                    img,
                    (final_x, final_y),
                    start_time=start_times[idx],
                    duration=0.3,
                    total_duration=total_durations
                )
                clips.append(img_clip)

                for i, text in enumerate(text_data):
                    if i == 0:
                        font_size = 50
                        ypos = (idx + 1) * 400 - 120
                        effect_type = 'typewriter' if len(text) > 2 else 'fade'
                    elif i == 1:
                        font_size = 40
                        ypos = (idx + 1) * 400 - 50
                        effect_type = 'fade'
                    elif i == 2:
                        font_size = 30
                        ypos = (idx + 1) * 400 + 10
                        effect_type = 'fade'
                    else:
                        font_size = 30
                        ypos = (idx + 1) * 400 + 60
                        effect_type = 'fade'

                    # 创建文本clip
                    tclip = self.create_text_with_effect(
                        text=text,
                        font_size=font_size,
                        font_name="STXINWEI",
                        color='white',
                        start_time=text_times[idx] + i * 0.2,
                        duration=total_durations - text_times[idx],
                        effect_type=effect_type
                    )
                    if idx % 2 == 0:
                        xpos = self.width - 380 - tclip.w
                    else:
                        xpos = 380
                    # 确保设置位置
                    tclip = tclip.with_position((xpos, ypos))
                    clips.append(tclip)

            audio_path = os.path.join(self.tmps, "merged_tts.mp3")
            final_audio.export(audio_path, format="mp3")
            bg_clip = ImageClip(bg_img_path).with_duration(total_durations)

            final_video = CompositeVideoClip([
                bg_clip,
                *clips,
            ], size=(self.width, self.height)).with_duration(total_durations)

            audio_clip = AudioFileClip(audio_path).with_start(0.5)
            bg_music = AudioFileClip(bgm_path).with_volume_scaled(0.1)

            if bg_music.duration < audio_clip.duration:
                loops = int(audio_clip.duration // bg_music.duration) + 1
                layered = [bg_music.with_start(i * bg_music.duration) for i in range(loops)]
                bg_music = CompositeAudioClip(layered)

            bg_music = bg_music.with_duration(audio_clip.duration)
            bg_music = bg_music.with_effects([AudioFadeOut(1)])

            final_audio_layers = [bg_music, audio_clip]
            final_audio_clip = CompositeAudioClip(final_audio_layers)

            final_video = final_video.with_audio(final_audio_clip)

            # 输出
            final_video.write_videofile(output_path,
                                        fps=30,
                                        codec="libx264",
                                        audio_codec="aac",
                                        audio_bitrate="192k",
                                        ffmpeg_params=["-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"])

            video_size = 0
            if os.path.exists(output_path):
                video_size = os.path.getsize(output_path)

            Video.objects.filter(id=video_id).update(
                result='Success',
                process=1.0,
                video_path=f"/media/videos/{video_id}.mp4",
                cost=time.time() - begin,
                size=video_size
            )

        except Exception as e:
            logger.error(traceback.format_exc())
            Video.objects.filter(id=video_id).update(result='Fail')
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e

        finally:
            if os.path.exists(self.tmps):
                shutil.rmtree(self.tmps)

    def create_deal_animation(self, img, final_position, start_time, duration, total_duration):

        img_array = np.array(img)
        img = ImageClip(img_array).with_duration(total_duration)

        start_pos = (self.width, -img.h)

        def position_func(t):
            if t < start_time:
                return start_pos
            elif start_time <= t < start_time + duration:
                lp = (t - start_time) / duration
                progres = 1 - (1 - lp) ** 2
                x = start_pos[0] + (final_position[0] - start_pos[0]) * progres
                y = start_pos[1] + (final_position[1] - start_pos[1]) * progres
                return (int(x), int(y))
            else:
                return final_position

        return img.with_position(position_func)

    def create_text_with_effect(self, text, font_size, font_name, color,
                                start_time, duration, effect_type='fade'):
        """创建带有特效的文本 - 修复版"""

        # 基础文本
        text_clip = TextClip(
            text=text,
            font_size=font_size,
            font=font_name,
            color=color,
            method="label",
            stroke_color='black',
            stroke_width=1
        ).with_start(start_time).with_duration(duration)

        if effect_type == 'fade':
            # 淡入效果 - 使用内置的FadeIn
            try:
                text_clip = text_clip.with_effects([CrossFadeIn(0.5)])
            except Exception as e:
                logger.warning(f"FadeIn失败: {e}")

        elif effect_type == 'typewriter':
            # 打字机效果 - 使用简化版本
            text_clip = text_clip.with_effects([vfx.SlideIn(1, "left")])

        return text_clip

    def prepare_background(self, bg_path, target_size=None, brightness_factor=0.2):
        if target_size is None:
            target_size = (self.width, self.height)
        img = PilImage.open(bg_path).convert("RGBA")
        img = img.resize(target_size, PilImage.LANCZOS)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_factor)
        tmp_bg_path = os.path.join(self.tmps, "tmp_bg.png")
        img.save(tmp_bg_path)
        return tmp_bg_path

    def generate_vertical_cover(self, title, img_path, user):
        cover_width, cover_height = 1080, 1464
        title_color = (255, 215, 0)
        stroke_color = (0, 0, 0)
        cover = PilImage.open(os.path.join(self.img_path, "1b6db0a6-91fb-4401-b60e-9ec1c51976dd.png")).resize((cover_width, cover_height))
        enhancer = ImageEnhance.Brightness(cover)
        cover = enhancer.enhance(0.2)
        img = self.img_utils.trim_image(img_path)
        new_w, new_h = img.size[0] * 2, img.size[1] * 2
        img = img.resize((new_w, new_h), PilImage.LANCZOS)
        img_x = (cover_width - new_w) // 2
        img_y = (cover_height - new_h) // 2
        cover.paste(img, (img_x, img_y), img)
        draw = ImageDraw.Draw(cover)
        font = ImageFont.truetype("msyhbd.ttc", 90)

        def split_title(title: str, width: int = 12):
            result = []
            parts = title.replace("，", ",").split(",")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                wrapped = textwrap.wrap(part, width=width)
                result.extend(wrapped)
            return result

        lines = split_title(title, width=12)
        line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 30
        text_y = cover_height // 2 - 150
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = (cover_width - text_w) // 2
            draw.text((text_x, text_y), line, font=font, fill=title_color, stroke_width=3, stroke_fill=stroke_color)
            text_y += line_height

        image_id = uuid.uuid4()
        image_name = f"{image_id}.png"
        cover.save(os.path.join(IMG_PATH, image_name))
        cover_size = os.path.getsize(os.path.join(IMG_PATH, image_name))
        spec = {'format': 'png', 'mode': 'RGBA', 'size': cover_size}

        Image(id=image_id, img_name=image_name, category='normal', img_path=IMG_PATH,
              width=cover_width, height=cover_height, creator=user, spec=spec).save()
        return image_id

    def generate_horizontal_cover(self, title, img_path, user):
        width, height = 1920, 1080

        bg = PilImage.open(os.path.join(self.img_path, "6b24e082-f935-4664-8bd4-4c9e228d44e8.png")).resize((width, height))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.2)

        target_width = int(width * 0.35)
        resized = []
        for path in img_path:
            img = self.img_utils.trim_image(path)
            ow, oh = img.size
            new_h = int(oh * (target_width / ow))
            resized.append(img.resize((target_width, new_h), PilImage.LANCZOS))

        left_img = resized[1]  # 第二张 → 左边
        center_img = resized[0]  # 第一张 → 中间（最高层）
        right_img = resized[2]  # 第三张 → 右边

        center_x = (width - center_img.width) // 2
        center_y = (height - center_img.height) // 2

        # 左图、右图偏移
        left_x = max(0, int(width // 3 - left_img.width))
        left_y = (height - left_img.height) // 2
        right_x = min(int(width - right_img.width), int(2 * width // 3))
        right_y = (height - right_img.height) // 2

        bg.paste(left_img, (left_x, left_y), left_img)
        bg.paste(right_img, (right_x, right_y), right_img)
        bg.paste(center_img, (center_x, center_y), center_img)

        draw = ImageDraw.Draw(bg)
        font = ImageFont.truetype("msyhbd.ttc", 120)
        title_color = (255, 215, 0)
        stroke_color = (0, 0, 0)

        def split_title(title: str, width: int = 14):
            result = []
            parts = title.replace("，", ",").split(",")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                wrapped = textwrap.wrap(part, width=width)
                result.extend(wrapped)
            return result

        lines = split_title(title, width=12)
        line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 30
        text_y = int(height * (1 - 0.618))
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = (width - text_w) // 2
            draw.text((text_x, text_y), line, font=font, fill=title_color, stroke_width=3, stroke_fill=stroke_color)
            text_y += line_height

        image_id = uuid.uuid4()
        image_name = f'{image_id}.png'
        bg.save(os.path.join(IMG_PATH, image_name))
        cover_size = os.path.getsize(os.path.join(IMG_PATH, image_name))
        spec = {
            'format': 'png',
            'mode': 'RGBA',
            'size': cover_size
        }

        Image(
            id=image_id,
            img_name=image_name,
            category='normal',
            img_path=IMG_PATH,
            width=width,
            height=height,
            creator=user,
            spec=spec
        ).save()

        return image_id
