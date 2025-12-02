import logging
import math
import os
import re
import textwrap
import time
import shutil
import traceback
import uuid

import numpy as np
from PIL import Image as PilImage, ImageDraw, ImageFont, ImageEnhance
from moviepy import *
from moviepy.audio.fx import AudioFadeOut
from pydub import AudioSegment

from astra.settings import VIDEO_PATH, IMG_PATH, TMP_PATH
from image.models import Image
from video.models import Video
from video.templates.video_template import VideoTemplate, VideoOrientation
from voice.models import Sound

logger = logging.getLogger("video")


class PlayerList(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '球员列表视频'
        self.desc = '通过一组球员以及相关数据生成视频'
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
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = "/media/videos/player_compare.mp4"
        self.default_speaker = None
        self.width, self.height = self.get_size(self.orientation)
        self.duration_start = 0
        self.cover = None
        self.video_type = 'Regular'
        self.tmps = None

    def process(self, user, video_id, parameters):
        """实现带字幕和音频同步的视频生成

        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
            :param user: 创建者
        """

        begin = time.time()  # 记录开始时间

        self.tmps = os.path.join(TMP_PATH, video_id)
        if not os.path.exists(self.tmps):
            os.mkdir(self.tmps)
        logger.info(f"视频生成请求参数：{parameters}")
        project_name = parameters.get('title')
        param_id = self.save_parameters(self.template_id, user, project_name, parameters)
        # 获取开场部分和视频主体内容
        start_text = parameters.get('start_text', '')

        bgm = parameters.get('bgm')  # 获取背景音乐路径
        bgm_sound = Sound.objects.get(id=bgm)
        bgm_path = os.path.join(self.sound_path, bgm_sound.sound_path)

        content = parameters.get('content')
        reader = parameters.get('reader')

        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")
        Video(creator=user, title=project_name,
              content=start_text, video_type=self.video_type,
              result='Process',
              process=0.0, id=video_id, param_id=param_id).save()

        try:
            bkg = parameters.get('background')  # 获取背景图片
            if bkg:
                bkg_img = Image.objects.get(id=bkg)
                bkg_path = os.path.join(self.img_path, bkg_img.img_name)
                bg_img_path = self.prepare_background(bkg_path)
            else:
                image = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 255))
                bg_img_path = os.path.join(self.tmps, "tmp_bg.png")
                # 保存图片
                image.save(bg_img_path)
            subtitlers = []
            # 从0.5秒开始有声音,start用来记录视频开头部分时长
            start = 0.5
            final_audio = AudioSegment.silent(duration=0)
            # 处理开场的音频和字幕
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
                        # 读取失败时，尝试按mp3或wav显式解码
                        try:
                            audio = AudioSegment.from_file(tts_path, format='mp3').fade_in(200).fade_out(200)
                        except Exception:
                            audio = AudioSegment.from_file(tts_path, format='wav').fade_in(200).fade_out(200)
                except Exception:
                    # 读取失败时，尝试按mp3或wav显式解码
                    try:
                        audio = AudioSegment.from_file(tts_path, format='mp3').fade_in(200).fade_out(200)
                    except Exception:
                        audio = AudioSegment.from_file(tts_path, format='wav').fade_in(200).fade_out(200)
                for text_clip in self.subtitler.text_clip(sg, start, tts.duration, 780, self.width):
                    subtitlers.append(text_clip)
                if i == 0:
                    final_audio = audio
                    start += tts.duration
                else:
                    final_audio = final_audio.append(audio, crossfade=200)
                    start += tts.duration - 0.2

            # 开场和主体内容切换前插入0.5秒静默等待
            final_audio = final_audio.append(AudioSegment.silent(duration=500))
            start += 0.5

            card_paths = []
            # 用来记录每一张卡片的持续时间
            content_durations = []
            # 记录原始图片路径（用于开场展示）
            original_paths = []
            content_subtitler_start = start

            for info in content:
                content_duration = 0
                text = info['text']

                segments = self.text_utils.split_text(text)
                for i, sg in enumerate(segments):
                    tts = self.speech.chat_tts(sg, reader, user, video_id)
                    # 同样增加回退逻辑，避免扩展不一致导致解码失败
                    tts_path = os.path.join(self.tts_path, f'{tts.id}.{tts.format}')
                    if not os.path.isfile(tts_path):
                        fallback_exts = ['mp3', 'wav'] if tts.format != 'mp3' else ['wav']
                        for ext in fallback_exts:
                            alt = os.path.join(self.tts_path, f'{tts.id}.{ext}')
                            if os.path.isfile(alt):
                                tts_path = alt
                                break

                    for text_clip in self.subtitler.text_clip(sg, content_subtitler_start, tts.duration, 780, self.width):
                        subtitlers.append(text_clip)
                    audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                    final_audio = final_audio.append(audio, crossfade=200)
                    content_duration += tts.duration - 0.2
                    content_subtitler_start += tts.duration - 0.2

                # 每段内容结束增加0.5秒静默切换等待
                final_audio = final_audio.append(AudioSegment.silent(duration=500))
                content_duration += 0.5
                content_subtitler_start += 0.5

                content_durations.append(content_duration)
                if os.path.isfile(info['image_path']):
                    card_img = info['image_path']
                else:
                    content_img = Image.objects.get(id=info['image_path'])
                    card_img = os.path.join(self.img_path, content_img.img_name)
                # 收集原始图片路径，以便开场展示
                original_paths.append(card_img)
                card_paths.append(self.build_player_card(card_img, info['chinese_name'], info['key_note'], info['stats'], info['accuracy']))
            audio_path = os.path.join(self.tmps, "merged_tts.mp3")
            final_audio.export(audio_path, format="mp3")

            cover_id = self.generate_vertical_cover(project_name, original_paths[-1], user)
            Video.objects.filter(id=video_id).update(vertical_cover=cover_id)

            horizontal_cover_id = self.generate_horizontal_cover(project_name, original_paths[-2:], user)
            Video.objects.filter(id=video_id).update(cover=horizontal_cover_id)

            if start < 3:
                start = 3

            total_durations = sum(content_durations) + start + 2

            clips = []

            font_path = "STXINWEI.TTF"
            font_size = 80
            font = ImageFont.truetype(font_path, font_size)

            # ---------- 开场：五张原图顺序入场并停留 ----------
            # 固定五个位置的x坐标：0, 384, 768, 1152, 1536（视频宽度1920，间隔384）
            last5 = original_paths[-5:] if len(original_paths) >= 5 else original_paths[:]

            # 入场动画：每张0.4s；相邻两张间隔0.1s；入场后上下小幅度移动
            entry_duration = 0.4
            entry_gap = 0.1  # 新的间隔
            start_time = 0.5
            for idx, img_path in enumerate(last5):
                # 先做透明裁剪
                try:
                    trimmed_img = self.img_utils.trim_image(img_path).convert("RGBA")
                except Exception:
                    trimmed_img = self.img_utils.trim_image(img_path).convert("RGB")
                # 等比缩放到高度 self.height - 200（保持宽高比）
                target_h = self.height - 200
                w0, h0 = trimmed_img.size
                scale = target_h / float(h0)
                new_w = max(1, int(w0 * scale))
                if new_w > self.width // 5 + 30:
                    new_w = self.width // 5 + 30
                trimmed_img = trimmed_img.resize((new_w, target_h), PilImage.LANCZOS)
                w, h = trimmed_img.size

                # 保存到临时文件并加载为ImageClip
                tmp_intro_path = os.path.join(self.tmps, f"intro_trim_{idx}.png")
                try:
                    trimmed_img.save(tmp_intro_path)
                except Exception:
                    tmp_intro_path = img_path
                if idx == 0:
                    target_x = int(self.width - w)
                elif idx == 1:
                    target_x = 0
                elif idx == 2:
                    target_x = 7 * self.width // 10 - w // 2
                elif idx == 3:
                    target_x = 3 * self.width // 10 - w // 2
                elif idx == 4:
                    target_x = (self.width - w) // 2
                else:
                    continue

                target_y = (self.height - h) // 2  # 以缩放后的高度居中

                start_y = -h

                # 创建 clip
                clip = ImageClip(tmp_intro_path).with_start(start_time + idx * entry_gap)
                clip = clip.with_duration(start - (start_time + idx * entry_gap))

                # 振幅（上下浮动像素）
                amplitude = 20
                frequency = 0.25  # 每4秒一次上下循环

                # 偶数序号图和奇数序号图反向浮动
                direction = 1 if idx % 2 == 1 else -1

                # 位置函数：先掉落，再浮动
                def pos_func(tt, sx=target_x, ty=target_y, sy=start_y,
                             drop=entry_duration, amp=amplitude, freq=frequency, dir=direction):

                    if tt <= drop:
                        # 0 → 1 归一化
                        p = self.ease_in_out(tt / drop)
                        # 从上方掉落到 target_y
                        y = sy + p * (ty - sy)
                        return (sx, y)
                    else:
                        # 到达后开始浮动
                        t2 = tt - drop
                        dy = dir * amp * math.sin(2 * math.pi * freq * t2)
                        return (sx, ty + dy)

                clip = clip.with_position(pos_func)

                clips.append(clip)

                start_time = round(start_time + entry_gap, 4)

            # ---------- 阶段1：第一张和第二张卡片同时进入，分别位于左侧和右侧位置 ----------
            # 按模板分辨率缩放卡片尺寸与位置
            movie_t = start
            card_w, card_h = 720, 960
            left_x = 180
            top_y = 120
            gap_x = 120
            positions = [(left_x, top_y), (left_x + card_w + gap_x, top_y)]
            first_card = card_paths[0]
            second_card = card_paths[1]
            # 卡片进入在开场五图结束后至少停留 1 秒再开始（movie_t 已在上方计算）
            duration_move = 1
            current_cards = []

            if first_card and second_card:
                first_duration = content_durations[0] + content_durations[1]

                # 第一张从左侧进入左侧位置
                sx1 = -card_w
                ex1, ey1 = positions[0]
                clip_first_left = ImageClip(first_card).with_start(movie_t).with_duration(first_duration)
                clip_first_left = clip_first_left.with_position(lambda tt, sx=sx1, ex=ex1, sy=ey1:
                                                                (sx + self.ease_in_out(min(tt / duration_move, 1)) * (ex - sx), sy))
                clips.append(clip_first_left)

                # 第二张从右侧进入右侧位置
                sx2 = self.width
                ex2, ey2 = positions[1]
                clip_second_right = ImageClip(second_card).with_start(movie_t).with_duration(first_duration)
                clip_second_right = clip_second_right.with_position(lambda tt, sx=sx2, ex=ex2, sy=ey2:
                                                                    (sx + self.ease_in_out(min(tt / duration_move, 1)) * (ex - sx), sy))
                clips.append(clip_second_right)

                # 更新当前展示的两张卡
                current_cards = [first_card, second_card]
                movie_t += first_duration
            # ---------- 阶段2：用两秒打出标题 ----------
            duration_typing = 2

            def make_frame(t):
                num_chars = int((t / duration_typing) * len(project_name))
                txt = project_name[:num_chars]
                img = PilImage.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                text_w, text_h = draw.textbbox((0, 0), txt, font=font)[2:]
                x = (self.width - text_w) // 2
                y = (self.height - text_h) // 2

                # 描边
                stroke_width = 1
                stroke_color = (255, 255, 255, 255)  # 白色描边
                fill_color = (255, 215, 0, 255)  # 金色填充
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), txt, font=font, fill=stroke_color)
                draw.text((x, y), txt, font=font, fill=fill_color)

                return np.array(img)

            typing_clip = VideoClip(make_frame, duration=duration_typing)
            clips.append(typing_clip)

            # ---------- 阶段3：标题上移到顶部 ----------
            font_test = ImageFont.truetype(font_path, font_size)
            text_w, text_h = ImageDraw.Draw(PilImage.new("RGB", (1, 1))).textbbox((0, 0), project_name, font=font_test)[2:]
            target_y = (120 - text_h) // 2  # 目标顶部位置

            title_clip = TextClip(
                text=project_name,
                font=font_path,
                font_size=font_size,
                color=(255, 215, 0, 255),
                stroke_color="white",
                stroke_width=1,
            ).with_start(2).with_duration(total_durations - 2)  # 一直持续到结束

            def move_title(t):
                if t < 0.2:
                    progress = min(1, t / 0.2)
                    y = self.height / 2 - (self.height / 2 - target_y) * self.ease_in_out(progress)
                else:
                    y = target_y
                return ("center", y)

            title_clip = title_clip.with_position(move_title)
            clips.append(title_clip)

            # 阶段4、后续卡片切换：右侧卡左移到左侧，新卡从右边进入右侧
            remaining_cards = card_paths[2:] if len(card_paths) > 2 else []
            for i, new_card in enumerate(remaining_cards):
                duration_stay = content_durations[i + 2] if i != len(remaining_cards) - 1 else content_durations[i + 2] + 2
                # 将右侧卡片移动到左侧位置
                sx, sy = positions[1]
                ex, _ = positions[0]
                clip_move = ImageClip(current_cards[1]).with_start(movie_t).with_duration(duration_stay)
                clip_move = clip_move.with_position(lambda tt, sx=sx, ex=ex, sy=sy:
                                                    (sx + self.ease_in_out(min(tt / duration_move, 1)) * (ex - sx), sy))
                clips.append(clip_move)

                # 新卡从右侧进入右侧位置
                start_x = self.width
                end_x, end_y = positions[1]
                clip_new = ImageClip(new_card).with_start(movie_t).with_duration(duration_stay)
                clip_new = clip_new.with_position(lambda tt, sx=start_x, ex=end_x, sy=end_y:
                                                  (sx + self.ease_in_out(min(tt / duration_move, 1)) * (ex - sx), sy))
                clips.append(clip_new)

                # 更新当前展示的两张卡
                current_cards = [current_cards[1], new_card]
                movie_t += duration_stay

            bg_clip = ImageClip(bg_img_path).with_duration(total_durations)

            final_video = CompositeVideoClip([
                bg_clip,
                *clips,
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
            final_audio = CompositeAudioClip(final_audio_layers)

            final_video = final_video.with_audio(final_audio)

            # 输出
            final_video.write_videofile(output_path, fps=24, audio_codec="aac")

            video_size = 0
            if os.path.exists(output_path):
                video_size = os.path.getsize(output_path)

            Video.objects.filter(id=video_id).update(result='Success', process=1.0, video_path=f"/media/videos/{video_id}.mp4",
                                                     cost=time.time() - begin, size=video_size)

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

    def build_player_card(self, image_path, name, key_note, stats, accuracy):
        # 根据模板分辨率按 1600x900 的基准比例缩放卡片尺寸

        card_width, card_height = 720, 960
        card = PilImage.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        img = self.img_utils.trim_image(image_path).convert("RGBA")
        w, h = img.size
        # 将图片按最佳尺寸缩放：限制在最大宽度720和最大高度840内，保持比例，允许对小图放大
        max_w = 720
        max_h = 900
        scale = min(max_w / w, max_h / h)
        if abs(scale - 1.0) > 1e-6:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), PilImage.LANCZOS)
            w, h = img.size
        # 高度小于基线则底对齐到 y=baseline，否则顶端对齐，水平居中
        baseline = 900
        y = baseline - h if h < baseline else 0
        x = (card_width - w) // 2
        card.alpha_composite(img, (x, y))

        # 字体按高度比例缩放
        font_name = ImageFont.truetype("STXINWEI.TTF", 36)
        font_key_note = ImageFont.truetype("STXINWEI.TTF", 38)
        font_stats = ImageFont.truetype("STXINWEI.TTF", 36)

        stats_items = [s for s in re.split(r"\s+", str(stats).strip()) if s]
        if stats_items:
            y_start, y_end = 60, 540
            if len(stats_items) == 1:
                ys = [(y_start + y_end) // 2]
            else:
                spacing = (y_end - y_start) / (len(stats_items) - 1)
                ys = [int(y_start + i * spacing) for i in range(len(stats_items))]
            for i, item in enumerate(stats_items):
                text_w = draw.textbbox((0, 0), item, font=font_stats)[2]
                margin_r = 24  # 右边距按宽度比例缩放
                text_x = card_width - margin_r - text_w
                self.draw_text_with_outline(draw, (text_x, ys[i]), item, font_stats,
                                            fill=(255, 255, 255, 255), outline_color=(0, 0, 0, 255), outline_width=1)

        # Name
        name_y1, name_y2 = 720, 780
        draw.rectangle([(0, name_y1), (card_width, name_y2)], fill=(95, 158, 160, 180))
        name_w = draw.textbbox((0, 0), name, font=font_name)[2]
        draw.text(((card_width - name_w) // 2, name_y1 + 12), name, fill=(255, 255, 255, 255), font=font_name)

        # Salary
        key_note_y1, key_note_y2 = 780, 840
        draw.rectangle([(0, key_note_y1), (card_width, key_note_y2)], fill=(255, 215, 0, 220))
        key_note_w = draw.textbbox((0, 0), key_note, font=font_key_note)[2]
        self.draw_text_with_outline(draw, ((card_width - key_note_w) // 2, key_note_y1 + 10), key_note,
                                    font_key_note, fill=(0, 0, 0, 255), outline_color=(255, 255, 255, 255))

        data_y1, data_y2 = 840, 960
        draw.rectangle([(0, data_y1), (card_width, data_y2)], fill=(95, 158, 160, 180))

        stats_text = str(stats)
        acc_text = str(accuracy)
        stats_w = draw.textbbox((0, 0), stats_text, font=font_stats)[2]
        acc_w = draw.textbbox((0, 0), acc_text, font=font_stats)[2]
        stats_x = (card_width - stats_w) // 2
        acc_x = (card_width - acc_w) // 2
        draw.text((stats_x, 852), stats_text, fill=(255, 255, 255, 255), font=font_stats)
        draw.text((acc_x, 900), acc_text, fill=(255, 255, 255, 255), font=font_stats)

        tmp_path = os.path.join(self.tmps, f"tmp_{uuid.uuid4()}.png")
        card.save(tmp_path)
        return tmp_path

    def prepare_background(self, bg_path, target_size=None, brightness_factor=0.3):
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

    def generate_vertical_cover(self, title, img_path, user):
        cover_width, cover_height = 1080, 1464
        title_color = (255, 215, 0)  # 金色
        stroke_color = (0, 0, 0)  # 黑色描边

        # 创建白色背景
        cover = PilImage.open(os.path.join(self.img_path, "1b6db0a6-91fb-4401-b60e-9ec1c51976dd.png")).resize((cover_width, cover_height))
        enhancer = ImageEnhance.Brightness(cover)
        cover = enhancer.enhance(0.2)

        # 打开原图并裁剪
        img = self.img_utils.trim_image(img_path)

        # 图片放大2倍
        new_w, new_h = img.size[0] * 2, img.size[1] * 2
        img = img.resize((new_w, new_h), PilImage.LANCZOS)

        # 贴在背景正中间
        img_x = (cover_width - new_w) // 2
        img_y = (cover_height - new_h) // 2
        cover.paste(img, (img_x, img_y), img)

        # 绘制标题文字
        draw = ImageDraw.Draw(cover)

        font = ImageFont.truetype("msyhbd.ttc", 90)

        def split_title(title: str, width: int = 12):
            result = []
            # 先按中文/英文逗号切割
            parts = title.replace("，", ",").split(",")

            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # 再按宽度切割
                wrapped = textwrap.wrap(part, width=width)
                result.extend(wrapped)

            return result

        # 自动换行（每行约12字）
        lines = split_title(title, width=12)
        line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 30

        # 标题位置（整体上移，靠图片下方偏中位置）
        text_y = cover_height // 2 - 150

        # 绘制每一行文字（居中 + 描边）
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = (cover_width - text_w) // 2

            # 先描边（多次偏移）
            draw.text((text_x, text_y), line, font=font,
                      fill=title_color, stroke_width=3, stroke_fill=stroke_color)
            text_y += line_height

        # 保存封面图片
        image_id = uuid.uuid4()
        image_name = f"{image_id}.png"
        cover.save(os.path.join(IMG_PATH, image_name))
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
            width=cover_width,
            height=cover_height,
            creator=user,
            spec=spec
        ).save()

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
