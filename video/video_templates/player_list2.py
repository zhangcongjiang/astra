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
from moviepy.video.fx import Resize as vfx_resize
from pydub import AudioSegment

from astra.settings import VIDEO_PATH, IMG_PATH, TMP_PATH
from image.models import Image
from video.models import Video
from video.video_templates.video_template import VideoTemplate, VideoOrientation
from voice.models import Sound

import os

import cv2
import numpy as np
from insightface.app import FaceAnalysis

logger = logging.getLogger("video")
app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0)


class PlayerList2(VideoTemplate):
    """竖版：球员列表视频模板（重新设计开场与卡片，单人逐段展示）"""

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '球员列表视频（竖版）'
        self.desc = '竖版视频：开头动态标题与单人卡片逐段展示'
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
                            'name': 'draft',
                            'label': '选秀信息',
                            'type': 'input',
                            'inputType': 'text',
                            'required': True,
                            'placeholder': '例如：2003年状元秀'
                        },
                        {
                            'name': 'key_note',
                            'label': '重点信息',
                            'type': 'input',
                            'inputType': 'text',
                            'required': True,
                            'placeholder': '例如：$40,000,000'
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
                        },
                        {
                            'name': 'text',
                            'label': '字幕文案',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入该球员的字幕文案。'
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

            subtitlers = []
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
                for text_clip in self.subtitler.text_clip(sg, start, tts.duration, 1350, self.width):
                    subtitlers.append(text_clip)
                if i == 0:
                    final_audio = audio
                    start += tts.duration
                else:
                    final_audio = final_audio.append(audio, crossfade=200)
                    start += tts.duration - 0.2

            final_audio = final_audio.append(AudioSegment.silent(duration=500))
            start += 0.5

            content_subtitler_start = start
            # 主体内容：逐段生成卡片与音频
            body_paths = []
            panel_infos = []
            content_durations = []
            original_paths = []

            for idx, info in enumerate(content):
                content_duration = 0
                text = info.get('text', '')
                segments = self.text_utils.split_text(text)
                for i, sg in enumerate(segments):
                    tts = self.speech.chat_tts(sg, reader, user, video_id)
                    tts_path = os.path.join(self.tts_path, f'{tts.id}.{tts.format}')
                    if not os.path.isfile(tts_path):
                        fallback_exts = ['mp3', 'wav'] if tts.format != 'mp3' else ['wav']
                        for ext in fallback_exts:
                            alt = os.path.join(self.tts_path, f'{tts.id}.{ext}')
                            if os.path.isfile(alt):
                                tts_path = alt
                                break

                    for text_clip in self.subtitler.text_clip(sg, content_subtitler_start, tts.duration, 1350, self.width):
                        subtitlers.append(text_clip)

                    audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                    final_audio = final_audio.append(audio, crossfade=200)
                    content_duration += tts.duration - 0.2
                    content_subtitler_start += tts.duration - 0.2
                final_audio = final_audio.append(AudioSegment.silent(duration=500))
                content_duration += 0.5
                content_subtitler_start += 0.5
                content_durations.append(content_duration)

                # 图片与面板信息
                img_val = info.get('image_path')
                if isinstance(img_val, str) and os.path.isfile(img_val):
                    card_img = img_val
                else:
                    content_img = Image.objects.get(id=img_val)
                    card_img = os.path.join(self.img_path, content_img.img_name)
                original_paths.append(card_img)
                # 统一预处理：trim + 按宽度 660 缩放，居中使用
                try:
                    base_img = self.img_utils.trim_image(card_img).convert("RGBA")
                except Exception:
                    base_img = PilImage.open(card_img).convert("RGBA")
                w0, h0 = base_img.size
                new_w = 660
                scale = new_w / float(w0)
                new_h = max(1, int(h0 * scale))
                base_img = base_img.resize((new_w, new_h), PilImage.LANCZOS)
                body_path = os.path.join(self.tmps, f"body_{idx}.png")
                try:
                    base_img.save(body_path, format="PNG", optimize=True)
                except Exception:
                    base_img.save(body_path)
                body_paths.append(body_path)
                panel_infos.append({
                    'name': info.get('chinese_name', info.get('name', '')),
                    'draft': info.get('draft', ''),
                    'key_note': info.get('key_note', ''),
                    'stats': info.get('stats', ''),
                    'accuracy': info.get('accuracy', '')
                })

            audio_path = os.path.join(self.tmps, "merged_tts.mp3")
            final_audio.export(audio_path, format="mp3")

            # 封面使用最后一段的原图
            if original_paths:
                cover_id = self.generate_vertical_cover(project_name, original_paths[-1], user)
                Video.objects.filter(id=video_id).update(vertical_cover=cover_id)
            if original_paths:
                horizontal_cover_id = self.generate_horizontal_cover(project_name, original_paths[-2:], user)
                Video.objects.filter(id=video_id).update(cover=horizontal_cover_id)

            if start < 2:
                start = 2

            total_durations = sum(content_durations) + start + 1

            clips = []
            font_path = "STXINWEI.TTF"
            font_size = 64
            font = ImageFont.truetype(font_path, font_size)

            # 打字标题
            duration_typing = 2

            def make_frame(t):
                num_chars = int((t / duration_typing) * len(project_name))
                txt = project_name[:num_chars]
                img = PilImage.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                text_w, text_h = draw.textbbox((0, 0), txt, font=font)[2:]
                x = (self.width - text_w) // 2
                y = 150

                # 描边
                stroke_width = 1
                stroke_color = (0, 0, 0, 255)
                fill_color = (255, 215, 0, 255)
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), txt, font=font, fill=stroke_color)
                draw.text((x, y), txt, font=font, fill=fill_color)

                return np.array(img)

            typing_clip = VideoClip(make_frame, duration=duration_typing).with_duration(total_durations)
            clips.append(typing_clip)

            # ===================== 下落动画（开场） =====================
            DROP_INTERVAL = 0.2
            DROP_TIME = 0.4

            # 选取最后五张图片
            start_images = original_paths[-5:]
            pil_imgs = [self.trim_image_center(p) for p in start_images]
            start_clips = []

            # 计算总时长，持续到 start - 0.1
            total_duration_start = start - 0.1  # 你的视频开场阶段持续到 start-0.1

            center_y = self.height // 2

            for i, pil_img in enumerate(pil_imgs):
                img_np = np.array(pil_img)
                clip = ImageClip(img_np)

                final_x = i * 180
                final_y = center_y - pil_img.height // 2
                start_y = -pil_img.height
                start_t = i * DROP_INTERVAL

                def make_pos(final_x, final_y, start_y, start_t):
                    def pos(t):
                        if t < start_t:

                            return final_x, start_y

                        elif t < start_t + DROP_TIME:
                            # 归一化时间 0~1
                            p = (t - start_t) / DROP_TIME
                            # 缓动公式（ease-out，重力下落效果）
                            # y = start + (end - start) * (1 - (1-p)^2)
                            y = start_y + (final_y - start_y) * (1 - (1 - p) ** 2)
                            return final_x, y
                        else:
                            return final_x, final_y

                    return pos

                start_clips.append(
                    clip
                    .with_start(0.5)
                    .with_duration(total_duration_start - 0.5)
                    .with_position(make_pos(final_x, final_y, start_y, start_t))
                )

            # 若 start 时间较长：开场只播放一轮后，第一张内容图提前进入；其后内容保持原计划开始时间
            intro_first_t = start
            accum = 0.0
            for i in range(len(body_paths)):
                duration_stay = content_durations[i] if i != 0 else content_durations[0] + start - intro_first_t
                baseline_t = intro_first_t + accum
                movie_t = intro_first_t if i == 0 else baseline_t
                body_img_path = body_paths[i]
                pil_img = PilImage.open(body_img_path).convert("RGBA")
                w0, h0 = pil_img.size
                target_w = 660
                scale0 = target_w / float(w0)
                target_h = max(1, int(h0 * scale0))
                base_img = pil_img.resize((target_w, target_h), PilImage.LANCZOS)
                tmp_content_path = os.path.join(self.tmps, f"content_trim_{i}.png")
                try:
                    base_img.save(tmp_content_path, format="PNG", optimize=True)
                except Exception:
                    base_img.save(tmp_content_path)
                # 球员姓名打字效果（持续1秒），位置 (100, 300)，图层在内容图片之下
                player_name = panel_infos[i].get('name', '')
                duration_typing_name = 1
                font_name = ImageFont.truetype("STXINWEI.TTF", 48)
                stroke_width = 1
                stroke_color = (0, 0, 0, 0)
                fill_color = (255, 255, 255, 255)

                def make_player_name_frame(t, name=player_name, duration=duration_typing_name, font=font_name):
                    num_chars = int((t / duration) * len(name))
                    txt = name[:max(0, num_chars)]
                    img = PilImage.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    for dx in range(-stroke_width, stroke_width + 1):
                        for dy in range(-stroke_width, stroke_width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((100 + dx, 300 + dy), txt, font=font, fill=stroke_color)
                    draw.text((100, 300), txt, font=font, fill=fill_color)
                    return np.array(img)

                name_clip = VideoClip(make_player_name_frame, duration=duration_typing_name).with_start(movie_t).with_duration(duration_stay)
                clips.append(name_clip)

                # 将内容图片在出现后缓慢放大到 1.05 倍，并实现 0.2s 右入居中
                body_clip = ImageClip(tmp_content_path).with_start(movie_t).with_duration(duration_stay)

                # 位置：从右滑入到居中（0.2s），之后保持居中
                center_x = (self.width - target_w) // 2
                center_y = (self.height - target_h) // 2
                start_x_right = self.width
                slide_dur = 0.3

                def _pos_body(t, slide=slide_dur):
                    # 根据当前缩放比例，动态调整左上角位置，使视觉中心保持不变
                    s = _scale_body(t, slide=slide)
                    offset_x = int((target_w * (s - 1.0)) / 2)
                    offset_y = int((target_h * (s - 1.0)) / 2)
                    if t < 0:
                        # 滑入前保持在画面右侧外，且中心对齐修正
                        return (start_x_right - offset_x, center_y - offset_y)
                    if t < slide:
                        k = min(1.0, t / max(1e-6, slide))
                        x = int(start_x_right + (center_x - start_x_right) * k) - offset_x
                        return (x, center_y - offset_y)
                    return (center_x - offset_x, center_y - offset_y)

                body_clip = body_clip.with_position(_pos_body)

                # 缩放：滑入阶段保持1.0，之后最多用时1.8s线性放大至1.05，并保持至结束

                def _scale_body(t, slide=slide_dur):
                    if t < 0:
                        return 1.0
                    if t < slide:
                        return 1.0
                    k = min(1.0, (t - slide) / 1.8)
                    return 1.0 + 0.05 * k

                body_clip = body_clip.with_effects([vfx_resize(_scale_body)])
                clips.append(body_clip)

                # 底部面板：略晚于主体出现
                panel_path, panel_h = self.build_bottom_panel(panel_infos[i])
                panel_start = movie_t + 0.2 + 0.05
                panel_dur = duration_stay - 0.2 - 0.05
                if panel_dur > 0:
                    panel_clip = ImageClip(panel_path).with_start(panel_start).with_duration(panel_dur)
                    panel_clip = panel_clip.with_position(("center", 1100))
                    clips.append(panel_clip)

                # 累计时间供后续片段使用
                accum += duration_stay

            bg_clip = ImageClip(bg_img_path).with_duration(total_durations)

            final_video = CompositeVideoClip([
                bg_clip,
                *clips,
                *start_clips,
                *subtitlers
            ], size=(self.width, self.height)).with_duration(content_subtitler_start + 1)

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

    def draw_text_with_outline(self, draw, pos, text, font, fill, outline_color=(0, 0, 0, 255), outline_width=1):
        x, y = pos
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        draw.text(pos, text, font=font, fill=fill)

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

    def ease_in_out(self, t):
        return 3 * t ** 2 - 2 * t ** 3

    def build_bottom_panel(self, panel: dict):
        """构建底部数据面板图片，返回 (path, height)。"""
        card_width = self.width - 200
        # 分为四块：姓名(70) -> draft(140) -> 关键数据(70) -> 统计数据(140)
        draft_h, key_h, data_h = 60, 60, 120

        card_height = draft_h + key_h + data_h
        img = PilImage.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 文本与字体
        font_draft = ImageFont.truetype("STXINWEI.TTF", 36)
        font_key_note = ImageFont.truetype("STXINWEI.TTF", 48)
        font_stats = ImageFont.truetype("STXINWEI.TTF", 36)

        # 数据
        draft_text = str(panel.get('draft', '') or '')
        key_note = str(panel.get('key_note', '') or '')
        stats = panel.get('stats', '')
        stats_text = " ".join(stats.split(" ")[:5])
        acc_text = str(panel.get('accuracy', '') or '')

        # 颜色：姓名/草稿/统计块用冷色，关键数据块高亮金色
        cadet_blue = (95, 158, 160, 180)
        gold = (255, 215, 0, 220)

        # 2) draft块（高度 70）
        draft_y1, draft_y2 = 0, draft_h
        draw.rectangle([(0, draft_y1), (card_width, draft_y2)], fill=cadet_blue)
        draft_w = draw.textbbox((0, 0), draft_text, font=font_draft)[2]
        # 垂直居中显示 draft 内容
        draw.text(((card_width - draft_w) // 2, draft_y1 + 12), draft_text, fill=(255, 255, 255, 255), font=font_draft)

        # 3) 关键数据块（高亮）
        key_note_y1, key_note_y2 = draft_y2, draft_y2 + key_h
        draw.rectangle([(0, key_note_y1), (card_width, key_note_y2)], fill=gold)
        key_note_w = draw.textbbox((0, 0), key_note, font=font_key_note)[2]
        self.draw_text_with_outline(draw, ((card_width - key_note_w) // 2, key_note_y1 + 6), key_note,
                                    font_key_note, fill=(0, 0, 0, 255), outline_color=(255, 255, 255, 255))

        # 4) 统计数据块（统计与命中率）
        data_y1, data_y2 = key_note_y2, key_note_y2 + data_h
        draw.rectangle([(0, data_y1), (card_width, data_y2)], fill=cadet_blue)
        stats_w = draw.textbbox((0, 0), stats_text, font=font_stats)[2]
        acc_w = draw.textbbox((0, 0), acc_text, font=font_stats)[2]
        stats_x = (card_width - stats_w) // 2
        acc_x = (card_width - acc_w) // 2
        draw.text((stats_x, data_y1 + 12), stats_text, fill=(255, 255, 255, 255), font=font_stats)
        draw.text((acc_x, data_y1 + 70), acc_text, fill=(255, 255, 255, 255), font=font_stats)

        path = os.path.join(self.tmps, f"panel_{uuid.uuid4()}.png")
        img.save(path)
        return path, card_height

    def trim_image_center(self, image_path, center_width=90, fixed_height=300):
        """
        先去掉透明边界（trim），再保留水平中间 target_width px，高度不变
        """
        img_rgba = self.img_utils.trim_image(image_path)
        # img_rgba = PilImage.open(image_path).convert("RGBA")
        img_rgba = np.array(img_rgba, dtype=np.uint8)

        h, w, _ = img_rgba.shape

        # 2️⃣ 丢弃 alpha，仅用于人脸检测
        img_bgr = cv2.cvtColor(img_rgba[:, :, :3], cv2.COLOR_RGB2BGR)

        # 3️⃣ 人脸检测
        faces = app.get(img_bgr)

        if faces:
            # 最大人脸
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            x1, y1, x2, y2 = map(int, face.bbox)
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            logger.info(f"{image_path}识别到人脸")
        else:
            center_x = w // 2
            center_y = h // 2
            logger.info(f"{image_path}没有识别到人脸")

        # 4️⃣ 中间 90px
        half_w = center_width // 2
        crop_left = max(0, center_x - half_w)
        crop_right = min(w, center_x + half_w)

        # 垂直方向裁剪
        half_h = fixed_height // 2
        crop_top = max(0, center_y - half_h)
        crop_bottom = min(h, center_y + half_h)

        cropped = img_rgba[crop_top:crop_bottom, crop_left:crop_right, :]

        return PilImage.fromarray(cropped).resize((2 * center_width, 2 * fixed_height), PilImage.LANCZOS)

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

        target_height = height - 100

        main_img = img_path[0]
        main_body = self.img_utils.trim_image(main_img)
        w, h = main_body.size
        new_w = int(w * target_height / h)
        main_body = main_body.resize((new_w, target_height), PilImage.LANCZOS)
        main_x = width // 4 - new_w // 2 + 20

        compared_img = img_path[1]
        compared_body = self.img_utils.trim_image(compared_img)
        w, h = compared_body.size
        new_w = int(w * target_height / h)
        compared_body = compared_body.resize((new_w, target_height), PilImage.LANCZOS)
        compared_x = width * 3 // 4 - new_w // 2 - 20

        bg.paste(main_body, (main_x, 50), main_body)
        bg.paste(compared_body, (compared_x, 50), compared_body)

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
