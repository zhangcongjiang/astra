import logging
import os
import re
import time
import shutil
import traceback
import uuid

import numpy as np
from PIL import Image as PilImage, ImageDraw, ImageFont, ImageEnhance
from moviepy import *
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

            card_paths = []
            # 用来记录每一张卡片的持续时间
            content_durations = []
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
                    audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                    for text_clip in self.subtitler.text_clip(sg, content_subtitler_start, tts.duration, 780, self.width):
                        subtitlers.append(text_clip)
                        final_audio = final_audio.append(audio, crossfade=200)
                        content_duration += tts.duration - 0.2
                        content_subtitler_start += tts.duration - 0.2
                content_durations.append(content_duration)
                if os.path.isfile(info['image_path']):
                    card_img = info['image_path']
                else:
                    content_img = Image.objects.get(id=info['image_path'])
                    card_img = os.path.join(self.img_path, content_img.img_name)
                card_paths.append(self.build_player_card(card_img, info['name'], info['key_note'], info['stats'], info['accuracy']))
            audio_path = os.path.join(self.tmps, "merged_tts.mp3")
            final_audio.export(audio_path, format="mp3")

            cover_id = self.generate_cover(project_name, card_paths, user)
            Video.objects.filter(id=video_id).update(cover=cover_id)

            total_durations = sum(content_durations) + start + 2

            clips = []

            font_path = "STXINWEI.TTF"
            font_size = 80
            font = ImageFont.truetype(font_path, font_size)

            # ---------- 阶段1：第一张和第二张卡片同时进入，分别位于左侧和右侧位置 ----------
            # 按模板分辨率缩放卡片尺寸与位置

            card_w, card_h = 720, 960
            left_x = 180
            top_y = 120
            gap_x = 120
            positions = [(left_x, top_y), (left_x + card_w + gap_x, top_y)]
            first_card = card_paths[0]
            second_card = card_paths[1]
            movie_t = 0  # 从标题上移后开始
            duration_move = 1
            current_cards = []

            if first_card and second_card:
                first_duration = content_durations[0] + content_durations[1] + start

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
            bg_music = AudioFileClip(bgm_path).with_volume_scaled(0.05)
            if bg_music.duration < audio_clip.duration:
                loops = int(audio_clip.duration // bg_music.duration) + 1
                layered = [bg_music.with_start(i * bg_music.duration) for i in range(loops)]
                bg_music = CompositeAudioClip(layered)
            bg_music = bg_music.with_duration(audio_clip.duration)

            # --- 合成音轨 ---
            final_audio = CompositeAudioClip([bg_music, audio_clip])

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

        card_width, card_height = 720, 900
        card = PilImage.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        img = self.img_utils.trim_image(image_path).convert("RGBA")
        w, h = img.size
        # 将图片按最佳尺寸缩放：限制在最大宽度500和最大高度700内，保持比例，允许对小图放大
        max_w = 720
        max_h = 840
        scale = min(max_w / w, max_h / h)
        if abs(scale - 1.0) > 1e-6:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), PilImage.LANCZOS)
            w, h = img.size
        # 高度小于基线则底对齐到 y=baseline，否则顶端对齐，水平居中
        baseline = 840
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

        # Stats 底部区域仅保留 accuracy
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

    def generate_cover(self, title, card_paths, user):
        # 创建空白背景，尺寸改为使用模板的 self.width 和 self.height
        width, height = self.width, self.height
        bg = PilImage.new("RGBA", (width, height), (0, 0, 0, 255))

        # 标题配置：固定字号为 100，顶部绘制
        font_path = "STXINWEI.TTF"
        font_size = int(80 * (self.height / 900.0))
        draw = ImageDraw.Draw(bg)
        font = ImageFont.truetype(font_path, font_size)

        # 文本换行：最大行宽为 (self.width - 200)，保证左右各预留 100px 边距
        def wrap_text(txt, font):
            draw_tmp = ImageDraw.Draw(PilImage.new("RGBA", (1, 1)))
            # 侧边距按宽度比例缩放（原始左右各100）
            side_margin = int(100 * (self.width / 1600.0))
            max_width = max(0, width - 2 * side_margin)
            lines = []
            current = ""
            for ch in txt:
                test = current + ch
                w = draw_tmp.textbbox((0, 0), test, font=font)[2]
                if w <= max_width or not current:
                    current = test
                else:
                    lines.append(current)
                    current = ch
            if current:
                lines.append(current)
            return lines

        # 绘制多行文本：在整幅宽度内水平居中
        def draw_multiline_center_with_clamp(img_draw, lines, font, base_y):
            line_spacing = int(10 * (self.height / 900.0))
            # 计算每行高度与总高度
            line_sizes = [img_draw.textbbox((0, 0), ln, font=font) for ln in lines] if lines else []
            heights = [(sz[3] - sz[1]) for sz in line_sizes]
            y = base_y
            container_left = 0
            container_width = width
            for idx, ln in enumerate(lines):
                bbox = img_draw.textbbox((0, 0), ln, font=font)
                lw = bbox[2] - bbox[0]
                local_x = max(0, min(container_width - lw, (container_width - lw) // 2))
                x = container_left + local_x
                # 白色描边 + 金色填充
                stroke_width = 1
                stroke_color = (255, 255, 255, 255)
                fill_color = (255, 215, 0, 255)
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx != 0 or dy != 0:
                            img_draw.text((x + dx, y + dy), ln, font=font, fill=stroke_color)
                img_draw.text((x, y), ln, font=font, fill=fill_color)
                if idx < len(heights) - 1:
                    y += heights[idx] + line_spacing
            # 返回文本总高度，供后续卡片定位使用
            total_text_h = sum(heights) + line_spacing * (len(heights) - 1) if heights else 0
            return total_text_h

        # 顶部绘制标题（从 y=30 开始）
        title_lines = wrap_text(title, font)
        _ = draw_multiline_center_with_clamp(draw, title_lines, font, base_y=int(10 * (self.height / 900.0)))

        # 贴上最后两张卡片到左右两侧位置（与阶段1一致）
        if len(card_paths) < 2:
            raise ValueError("card_paths 至少需要 2 张图片用于封面左右展示")
        left_card_path = card_paths[-2]
        right_card_path = card_paths[-1]

        # 阶段1中的卡片尺寸与位置
        scale_w = self.width / 1600.0
        scale_h = self.height / 900.0
        card_w, card_h = int(600 * scale_w), int(800 * scale_h)
        left_x = int(150 * scale_w)
        top_y = int(100 * scale_h)
        gap_x = int(100 * scale_w)
        positions = [(left_x, top_y), (left_x + card_w + gap_x, top_y)]

        # 左侧卡片
        left_card = PilImage.open(left_card_path).convert("RGBA")
        left_card_resized = left_card.resize((card_w, card_h), PilImage.LANCZOS)
        bg.alpha_composite(left_card_resized, positions[0])

        # 右侧卡片
        right_card = PilImage.open(right_card_path).convert("RGBA")
        right_card_resized = right_card.resize((card_w, card_h), PilImage.LANCZOS)
        bg.alpha_composite(right_card_resized, positions[1])

        # 保存封面图片
        image_id = uuid.uuid4()
        image_name = f"{image_id}.png"
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
