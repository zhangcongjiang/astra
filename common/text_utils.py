import math


class TextUtils:
    @staticmethod
    def split_title(text, ratio=(3, 2)):
        total_length = len(text)
        cut_length = int(total_length * (ratio[0] / float(sum(ratio))))

        # 按照字符切割文本
        part1 = text[:cut_length]
        part2 = text[cut_length:]

        return part1, part2

    @staticmethod
    def split_text(text, max_length=32):
        words = text.replace(' ', '').replace('-', '').replace('·', '').replace(':', ',').split('。')
        segments = []
        for word in words:
            length = 0
            for char in word:
                if char.isdigit():
                    length += 0.5
                else:
                    length += 1
            if length > max_length:
                word_2 = word.split('，')
                for i, item in enumerate(word_2):
                    if len(item) > max_length:
                        lines = math.ceil(len(item) / max_length)
                        for j in range(lines):
                            msg = item[max_length * j:max_length * (j + 1)]
                            if msg:
                                segments.append(msg)
                    else:
                        if item:
                            segments.append(item)
            else:
                if word:
                    segments.append(word)

        return segments
