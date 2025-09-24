import re
from moviepy import TextClip, CompositeVideoClip
from PIL import ImageFont


class SubtitlerUtils:
    def __init__(self, font_path="STXINWEI", font_size=40, line_spacing=10):
        self.font_path = font_path
        self.font_size = font_size
        self.line_spacing = line_spacing  # 行间距

    def tokenize(self, text):
        pattern = r'(\d+(\.\d+)?%?)|([A-Za-z]+)|([\u4e00-\u9fff])|([，。！？、；：,.!?])'
        tokens = re.findall(pattern, text)
        return [t[0] or t[2] or t[3] or t[4] for t in tokens if any(t)]

    def wrap_text(self, text, max_width):
        font = ImageFont.truetype(self.font_path, self.font_size)
        tokens = self.tokenize(text)

        lines = []
        current_line = ""

        for token in tokens:
            test_line = current_line + token
            try:
                w, _ = font.getsize(test_line)
            except AttributeError:
                bbox = font.getbbox(test_line)
                w = bbox[2] - bbox[0]

            if w <= max_width - 100:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = token

        if current_line:
            lines.append(current_line)

        return lines  # 返回 list 而不是拼接字符串

    def text_clip(self, text, start, duration, subtitler_height, max_width):
        lines = self.wrap_text(text, max_width - 100)

        for idx, line in enumerate(lines):
            txt_clip = TextClip(
                text=line,
                font=self.font_path,
                font_size=self.font_size,
                color="lightyellow",
                stroke_color='black',
                stroke_width=2,
                method="label",
                transparent=True,
            ).with_opacity(0.7).with_start(start).with_duration(duration - 0.2)

            # 水平居中，垂直位置根据行号调整
            y = subtitler_height + idx * (self.font_size + self.line_spacing)
            txt_clip = txt_clip.with_position(('center', y))
            yield txt_clip
