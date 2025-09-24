import re
from typing import List


class TextUtils:
    def __init__(self, max_length: int = 20):
        self.max_length = max_length
        self.punctuation_weights = {
            '。': 4, '！': 4, '？': 4,  # 句子结束
            '；': 3, '，': 2, '、': 2,  # 句子中间
            ' ': 1, '\n': 1,  # 空格和换行
            ',': 2, '!': 2, '?': 2  # 英文标点
        }

    def calculate_length(self, text: str) -> float:
        return sum(0.5 if char.isdigit() or char.isalpha() else 1
                   for char in text)

    def find_best_split_pos(self, text: str, start: int, end: int) -> int:
        best_pos = -1
        best_weight = 0
        for i in range(start, min(end, len(text))):
            char = text[i]
            if char in self.punctuation_weights:
                weight = self.punctuation_weights[char]
                if weight > best_weight:
                    best_weight = weight
                    best_pos = i
        return best_pos

    def split_text_by_length(self, text: str) -> List[str]:
        """对一段文本按长度切分"""
        segments = []
        remaining_text = text.strip()
        while remaining_text:
            if self.calculate_length(remaining_text) <= self.max_length:
                segments.append(remaining_text)
                break

            search_end = min(len(remaining_text), int(self.max_length * 1.5))
            split_pos = self.find_best_split_pos(remaining_text,
                                                 int(self.max_length * 0.8),
                                                 search_end)
            if split_pos > 0:
                segments.append(remaining_text[:split_pos + 1])
                remaining_text = remaining_text[split_pos + 1:].lstrip()
            else:
                segments.append(remaining_text)
                break
        return segments

    def split_text(self, text: str) -> List[str]:
        """先按标点符号切分，再按长度切分，返回段落不带标点"""
        # 构造正则匹配所有标点
        punctuation_chars = ''.join(self.punctuation_weights.keys())

        # 按标点分割，同时保留标点
        initial_segments = re.split(f'([{re.escape(punctuation_chars)}])', text)

        combined_segments = []
        for i in range(0, len(initial_segments) - 1, 2):
            segment = (initial_segments[i] + initial_segments[i + 1]).strip()
            if segment:
                # 去掉段尾标点
                if segment[-1] in punctuation_chars:
                    segment = segment[:-1]
                combined_segments.append(segment)

        # 处理末尾没有标点的部分
        if len(initial_segments) % 2 != 0 and initial_segments[-1].strip():
            combined_segments.append(initial_segments[-1].strip())

        # 对每段再按长度切分
        final_segments = []
        for seg in combined_segments:
            final_segments.extend(self.split_text_by_length(seg))

        return final_segments
