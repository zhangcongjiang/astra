import logging
import os
import time
import shutil
import traceback
import uuid

import numpy as np
from PIL import Image as PilImage, ImageDraw, ImageFont, ImageEnhance
from moviepy import *
from pydub import AudioSegment

from astra.settings import VIDEO_PATH, LOGO_PATH, IMG_PATH, TMP_PATH
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
        start_text = parameters.get('start_text', '').replace('·', '')

        bgm = parameters.get('bgm')  # 获取背景音乐路径
        bgm_sound = Sound.objects.get(id=bgm)
        bgm_path = os.path.join(self.sound_path, bgm_sound.sound_path)
        bkg = parameters.get('background')  # 获取背景图片
        bkg_img = Image.objects.get(id=bkg)
        bkg_path = os.path.join(self.img_path, bkg_img.img_name)
        content = parameters.get('content')
        reader = parameters.get('reader')

        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")
        Video(creator=user, title=project_name,
              content=content, video_type=self.video_type,
              result='Process',
              process=0.0, id=video_id, param_id=param_id).save()

        card_w, card_h = 500, 800
        try:

            bg_img_path = self.prepare_background(bkg_path)

            subtitlers = []
            # 从0.5秒开始有声音,start用来记录视频开头部分时长
            start = 0.5
            final_audio = AudioSegment.silent(duration=0)
            # 处理开场的音频和字幕
            start_segments = self.text_utils.split_text(start_text)
            for i, sg in enumerate(start_segments):
                tts = self.speech.chat_tts(sg, reader, user, video_id)
                tts_path = os.path.join(self.tts_path, f'{tts.id}.{tts.format}')
                audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                for text_clip in self.subtitler.text_clip(sg, start, tts.duration, 660, self.width):
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

            for index, info in enumerate(content):
                content_duration = 0
                text = info['text']
                segments = self.text_utils.split_text(text)
                for i, sg in enumerate(segments):
                    tts = self.speech.chat_tts(sg, reader, user, video_id)
                    tts_path = os.path.join(self.tts_path, f'{tts.id}.{tts.format}')
                    audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                    for text_clip in self.subtitler.text_clip(sg, content_subtitler_start, tts.duration, 660, self.width):
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
                card_paths.append(self.build_player_card(card_img, info['name'], info['key_note'], info['stats'], info['accuracy'],
                                                         f"#{len(content) - index}"))
            audio_path = os.path.join(self.tmps, "merged_tts.mp3")
            final_audio.export(audio_path, format="mp3")

            cover_id = self.generate_cover(project_name, bg_img_path, card_paths, user)
            Video.objects.filter(id=video_id).update(cover=cover_id)
            _cover = Image.objects.get(id=cover_id)
            cover_img_path = os.path.join(self.img_path, _cover.img_name)
            cover_img = PilImage.open(cover_img_path).convert("RGBA")
            cover_clip = ImageClip(np.array(cover_img)).with_duration(0.1)

            positions = [(20, 100), (20 + card_w + 30, 100), (20 + 2 * (card_w + 30), 100)]

            clips = []

            font_path = "STXINWEI.TTF"
            font_size = 80
            font = ImageFont.truetype(font_path, font_size)
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

            # ---------- 阶段2：标题上移到顶部 ----------
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
            ).with_start(2).with_duration(30 - 2)  # 一直持续到结束

            def move_title(t):
                if t < 0.2:
                    progress = min(1, t / 0.2)
                    y = self.height / 2 - (self.height / 2 - target_y) * self.ease_in_out(progress)
                else:
                    y = target_y
                return ("center", y)

            title_clip = title_clip.with_position(move_title)
            clips.append(title_clip)

            # ---------- 阶段3：前三张卡从右侧依次飞入 ----------
            t = 2.2
            duration_in = 0.6
            duration_stay = 4

            for idx, card in enumerate(card_paths[:3]):
                start_x = self.width
                end_x, end_y = positions[idx]
                clip = ImageClip(card).with_start(t).with_duration(start + content_durations[0] + content_durations[1] - t)
                clip = clip.with_position(lambda tt, sx=start_x, ex=end_x, sy=end_y:
                                          (sx + self.ease_in_out(min(tt / duration_in, 1)) * (ex - sx),
                                           sy if tt < duration_in else sy))
                clips.append(clip)
                t += duration_in  # 每张卡延迟开始进入（依次进场）
            t += duration_stay  # 所有卡展示完后再进入下阶段

            # ---------- 阶段4：后续卡片切换（带额外一轮左移，确保最后一张到达 positions[1]） ----------
            remaining_cards = card_paths[3:]
            current_cards = card_paths[:3]
            duration_move = 1
            duration_stay = 4  # 与上面保持一致

            for i, new_card in enumerate(remaining_cards):
                # 每轮：把当前 positions[1] 和 positions[2] 的卡向左移动一格，
                # 然后新卡从右侧进入 positions[2]
                for idx in [1, 2]:
                    sx, sy = positions[idx]
                    ex, ey = positions[idx - 1]
                    clip = ImageClip(current_cards[idx]).with_start(t).with_duration(duration_move + duration_stay)
                    # 冻结 sx, ex, sy 到 lambda 默认参数，避免闭包问题
                    clip = clip.with_position(lambda tt, sx=sx, ex=ex, sy=sy:
                                              (sx + self.ease_in_out(min(tt / duration_move, 1)) * (ex - sx), sy))
                    clips.append(clip)

                # 新卡从屏幕右侧进入，默认结束在 positions[2]
                start_x = self.width
                end_x, end_y = positions[2]
                clip_new = ImageClip(new_card).with_start(t).with_duration(duration_move + duration_stay)
                clip_new = clip_new.with_position(lambda tt, sx=start_x, ex=end_x, sy=end_y:
                                                  (sx + self.ease_in_out(min(tt / duration_move, 1)) * (ex - sx), sy))
                clips.append(clip_new)

                # 更新 current_cards 队列
                current_cards = current_cards[1:] + [new_card]
                t += duration_move + duration_stay

            # ---------- 额外一轮左移（没有新卡），把当前位于 positions[2] 的卡推进到 positions[1] ----------
            # 这样最后一张就能最终停在 positions[1]
            duration_final_move = 1
            for idx in [1, 2]:
                sx, sy = positions[idx]
                ex, ey = positions[idx - 1]
                clip = ImageClip(current_cards[idx]).with_start(t).with_duration(duration_final_move + duration_stay)
                clip = clip.with_position(lambda tt, sx=sx, ex=ex, sy=sy:
                                          (sx + self.ease_in_out(min(tt / duration_final_move, 1)) * (ex - sx), sy))
                clips.append(clip)

            t += duration_final_move
            bg_clip = ImageClip(bg_img_path).with_duration(start + sum(content_durations))

            final_video = CompositeVideoClip([
                bg_clip,
                cover_clip,
                *clips,
                *subtitlers
            ], size=(self.width, self.height)).with_duration(content_subtitler_start + 1)
            audio_clip = AudioFileClip(audio_path).with_start(0.5)
            bg_music = AudioFileClip(bgm_path).with_volume_scaled(0.05)
            if bg_music.duration < audio_clip.duration:
                loops = int(audio_clip.duration // bg_music.duration) + 1
                bg_music = bg_music.loop(n=loops)
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

    def build_player_card(self, image_path, name, key_note, stats, accuracy, index="#1"):
        card_width, card_height = 500, 800
        card = PilImage.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        img = self.img_utils.trim_image(image_path).convert("RGBA")
        w, h = img.size
        y = 600 - h if h < 600 else 0
        x = (card_width - w) // 2
        card.alpha_composite(img, (x, y))

        font_index = ImageFont.truetype("STXINWEI.TTF", 38)
        font_name = ImageFont.truetype("STXINWEI.TTF", 30)
        font_key_note = ImageFont.truetype("STXINWEI.TTF", 32)
        font_stats = ImageFont.truetype("STXINWEI.TTF", 26)

        draw.text((15, 30), index, fill=(255, 255, 255, 255), font=font_index)

        # Name
        name_y1, name_y2 = 600, 650
        draw.rectangle([(0, name_y1), (card_width, name_y2)], fill=(95, 158, 160, 180))
        name_w = draw.textbbox((0, 0), name, font=font_name)[2]
        draw.text(((card_width - name_w) // 2, name_y1 + 10), name, fill=(255, 255, 255, 255), font=font_name)

        # Salary
        key_note_y1, key_note_y2 = 650, 700
        draw.rectangle([(0, key_note_y1), (card_width, key_note_y2)], fill=(255, 215, 0, 220))
        key_note_w = draw.textbbox((0, 0), key_note, font=font_key_note)[2]
        self.draw_text_with_outline(draw, ((card_width - key_note_w) // 2, key_note_y1 + 8), key_note,
                                    font_key_note, fill=(0, 0, 0, 255), outline_color=(255, 255, 255, 255))

        # Stats
        data_y1, data_y2 = 700, 800
        draw.rectangle([(0, data_y1), (card_width, data_y2)], fill=(95, 158, 160, 180))
        draw.text((20, 710), stats, fill=(255, 255, 255, 255), font=font_stats)
        draw.text((20, 750), accuracy, fill=(255, 255, 255, 255), font=font_stats)

        tmp_path = os.path.join(self.tmps, f"tmp_{index}.png")
        card.save(tmp_path)
        return tmp_path

    def prepare_background(self, bg_path, target_size=(1600, 900), brightness_factor=0.5):
        img = PilImage.open(bg_path).convert("RGBA")
        img = img.resize(target_size, PilImage.LANCZOS)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_factor)
        tmp_bg_path = os.path.join(self.tmps, "tmp_bg.png")
        img.save(tmp_bg_path)
        return tmp_bg_path

    def ease_in_out(self, t):
        return 3 * t ** 2 - 2 * t ** 3

    def generate_cover(self, title, bkg_path, card_paths, user):
        font_path = "STXINWEI.TTF"
        font_size = 80
        bg = PilImage.open(bkg_path).convert("RGBA")

        # 2. 准备字体和绘制对象
        draw = ImageDraw.Draw(bg)
        font = ImageFont.truetype(font_path, font_size)

        text_w, text_h = ImageDraw.Draw(PilImage.new("RGB", (1, 1))).textbbox((0, 0), title, font=font)[2:]
        target_y = (120 - text_h) // 2
        target_x = (self.width - text_w) // 2

        # 4. 绘制带描边的标题（类似 MoviePy stroke 效果）
        outline_color = "white"
        for dx in [-1, 1, 0, 0]:
            for dy in [0, 0, -1, 1]:
                draw.text((target_x + dx, target_y + dy), title, font=font, fill=outline_color)
        draw.text((target_x, target_y), title, font=font, fill=(255, 215, 0))  # 金色文字

        # 5. 放置卡片（倒序）
        positions = [(20, 100), (550, 100), (1080, 100)]
        if len(card_paths) < 3:
            raise ValueError("card_paths 至少需要 3 张图片")

        last_three = card_paths[-3:][::-1]  # 倒序排列（最后→第一个）
        for pos, card_path in zip(positions, last_three):
            card = PilImage.open(card_path).convert("RGBA")
            bg.alpha_composite(card, dest=pos)

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
            width=1200,
            height=1600,
            creator=user,
            spec=spec
        ).save()

        return image_id
