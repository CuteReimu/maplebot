"""数字华容道 (3x3 滑块拼图)

生成一个随机可解的 3×3 数字华容道题目，用 A* 算法求解，
将求解过程渲染成 GIF 动图，以 base64 字符串返回。
"""
from __future__ import annotations

import base64
import heapq
import io
import random
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from nonebot.log import logger

# ─── 可移动方向表（下标 → 可交换的邻居下标）───
_DIRECTIONS: dict[int, list[int]] = {
    0: [1, 3],
    1: [0, 2, 4],
    2: [1, 5],
    3: [0, 4, 6],
    4: [1, 3, 5, 7],
    5: [2, 4, 8],
    6: [3, 7],
    7: [4, 6, 8],
    8: [5, 7],
}

_TARGET_HASH = 123456780  # 1 2 3 / 4 5 6 / 7 8 0


# ─── 辅助函数 ────────────────────────────────────────────────────────────────

def _dist(a: list[int]) -> int:
    """曼哈顿距离启发值"""
    d = 0
    for i, v in enumerate(a):
        if v == 0:
            continue
        v -= 1
        d += abs(i % 3 - v % 3)
        d += abs(i // 3 - v // 3)
    return d


def _hash_state(a: list[int]) -> int:
    h = 0
    for v in a:
        h = h * 10 + v
    return h


def _state_from_hash(h: int) -> list[int]:
    digits: list[int] = []
    for _ in range(9):
        digits.append(h % 10)
        h //= 10
    digits.reverse()
    return digits


# ─── 题目生成 ─────────────────────────────────────────────────────────────────

def _generate_problem() -> list[int]:
    """
    随机生成一个可解的 3×3 数字华容道（逆序数为偶数且曼哈顿距离 ≥ 10），
    最多尝试 1000 次。
    """
    tiles = list(range(1, 9))
    for _ in range(1000):
        random.shuffle(tiles)
        inversion_count = sum(
            1
            for i in range(len(tiles))
            for j in range(i)
            if tiles[j] > tiles[i]
        )
        candidate = tiles + [0]
        if inversion_count % 2 == 0 and _dist(candidate) >= 10:
            return candidate
    raise RuntimeError("生成数字华容道题目失败，请重试")


# ─── A* 求解 ─────────────────────────────────────────────────────────────────

def _solve(problem: list[int]) -> list[int]:
    """
    使用 A* 算法求解 3×3 数字华容道。
    返回从初始状态到目标状态的哈希序列（含首尾）。
    """
    start_hash = _hash_state(problem)

    # results[hash] = (last_hash_or_None, g_cost)
    results: dict[int, tuple[Optional[int], int]] = {start_hash: (None, 0)}
    close_set: set[int] = set()

    # 优先队列元素：(f, counter, state_hash, state_list)
    counter = 0
    open_heap: list[tuple[int, int, int, list[int]]] = [
        (_dist(problem), counter, start_hash, problem[:])
    ]

    while open_heap:
        _f, _c, h, p = heapq.heappop(open_heap)

        if h in close_set:
            continue

        if h == _TARGET_HASH:
            # 回溯路径
            path: list[int] = []
            cur: Optional[int] = h
            while cur is not None:
                path.append(cur)
                cur = results[cur][0]
            path.reverse()
            return path

        close_set.add(h)

        g = results[h][1]
        index0 = p.index(0)

        for idx in _DIRECTIONS[index0]:
            new_p = p[:]
            new_p[index0], new_p[idx] = new_p[idx], new_p[index0]
            new_hash = _hash_state(new_p)
            new_g = g + 1
            new_f = new_g + _dist(new_p)

            if new_hash not in close_set:
                prev = results.get(new_hash)
                if prev is None or new_g < prev[1]:
                    results[new_hash] = (h, new_g)
                    counter += 1
                    heapq.heappush(open_heap, (new_f, counter, new_hash, new_p))

    raise RuntimeError("数字华容道无解（不应发生）")


# ─── 帧渲染 ──────────────────────────────────────────────────────────────────

_CELL = 34          # 每格像素大小
_SIZE = _CELL * 3   # 整图 102×102


def _load_font(size: int = 20) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


_FONT = _load_font(20)

_COLOR_BG = (255, 255, 255)
_COLOR_BORDER = (0, 0, 0)
_COLOR_TEXT = (0, 0, 0)
_COLOR_EMPTY = (220, 220, 220)


def _draw_frame(state_hash: int) -> Image.Image:
    """根据状态哈希绘制一帧拼图图像（102×102 RGB）"""
    digits = _state_from_hash(state_hash)

    img = Image.new("RGB", (_SIZE, _SIZE), _COLOR_BG)
    draw = ImageDraw.Draw(img)

    for i, v in enumerate(digits):
        row, col = divmod(i, 3)
        x0 = col * _CELL
        y0 = row * _CELL
        x1 = x0 + _CELL - 1
        y1 = y0 + _CELL - 1

        fill = _COLOR_EMPTY if v == 0 else _COLOR_BG
        draw.rectangle([x0, y0, x1, y1], fill=fill, outline=_COLOR_BORDER, width=2)

        if v != 0:
            text = str(v)
            try:
                bbox = draw.textbbox((0, 0), text, font=_FONT)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except AttributeError:
                tw, th = _FONT.getsize(text)  # pylint: disable=no-member
            tx = x0 + (_CELL - tw) // 2
            ty = y0 + (_CELL - th) // 2
            draw.text((tx, ty), text, fill=_COLOR_TEXT, font=_FONT)

    return img


# ─── 对外接口 ─────────────────────────────────────────────────────────────────

def generate_slide_puzzle_gif() -> str:
    """
    生成数字华容道求解动图。
    返回 GIF 的 base64 编码字符串（不含前缀）。

    GIF 帧间延迟 1 秒，最后一帧额外停留 2 秒（共 3 秒）。
    """
    logger.info("[slide_puzzle] 生成题目并求解...")
    problem = _generate_problem()
    path = _solve(problem)
    logger.info(f"[slide_puzzle] 求解完成，共 {len(path)} 帧")

    frames = [_draw_frame(h) for h in path]

    # 转换为调色板模式（GIF 要求），quantize() 直接返回 "P" mode Image
    palette_frames = [f.quantize(colors=256) for f in frames]

    # 帧延迟：单位 ms（PIL 使用 ms，Go 原版使用百分之一秒×100=1s）
    delays = [1000] * len(palette_frames)
    if delays:
        delays[-1] = 3000  # 最后一帧展示 3 秒

    buf = io.BytesIO()
    palette_frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=palette_frames[1:],
        duration=delays,
        loop=0,
        optimize=False,
    )
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
