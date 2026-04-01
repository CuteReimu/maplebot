"""词条消息的序列化 / 反序列化 + 图片本地缓存管理"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from typing import Any

import httpx
from nonebot.adapters.onebot.v11 import Message as V11Message, MessageSegment as V11Seg

logger = logging.getLogger("maplebot.dict_entry")

# ---- 图片缓存目录 ----
_CACHE_DIR = os.path.join("chat_images")
os.makedirs(_CACHE_DIR, exist_ok=True)


# ===========================================================================
# 序列化（存词条）
# ===========================================================================

def serialize_message(msg: V11Message) -> str:
    """
    将 OneBot V11 Message 序列化为 JSON 字符串存入词条数据库。

    图片段：
      - 若有 url 字段，则异步下载后存到 chat_images/<md5>.ext，
        JSON 中记录 {"type":"image","data":{"file":"<local_path>","url":"<原url>","cached_at":<timestamp>}}
      - 若没有 url（例如通过 file:// 传来的），直接保留 file 字段

    文本段：直接保留。
    其他段：保留原始结构。
    """
    segments: list[dict[str, Any]] = []
    for seg in msg:
        seg_type: str = seg.type
        data: dict = dict(seg.data)

        if seg_type == "image":
            url: str = data.get("url", "") or data.get("file", "")
            local_file = data.get("file", "")

            # 如果已经是本地文件引用，直接保留
            if local_file.startswith("file://") or os.path.isfile(local_file):
                segments.append({"type": "image", "data": {"file": local_file}})
                continue

            # 否则尝试下载
            if url:
                saved_path = _download_image(url)
                if saved_path:
                    segments.append({
                        "type": "image",
                        "data": {
                            "file": saved_path,
                            "url": url,
                            "cached_at": int(time.time()),
                        },
                    })
                    continue
                # 下载失败：退回保存原 URL
                segments.append({"type": "image", "data": {"url": url, "cached_at": 0}})
                continue

            # 没有任何可用引用，跳过
            logger.warning("图片段无可用 url，已跳过: %s", data)

        else:
            segments.append({"type": seg_type, "data": data})

    return json.dumps(segments, ensure_ascii=False)


def _download_image(url: str) -> str | None:
    """
    同步下载图片到 chat_images/，返回本地路径（以 file:// 开头）。
    文件名使用 URL 的 MD5 作为唯一标识，保留后缀。
    下载失败返回 None。
    """
    try:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        # 尝试从 URL 提取后缀
        url_path = url.split("?")[0].rstrip("/")
        ext = os.path.splitext(url_path)[1]
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
            ext = ".jpg"
        filename = f"{url_hash}{ext}"
        local_path = os.path.join(_CACHE_DIR, filename)

        if os.path.exists(local_path):
            logger.debug("图片已缓存，跳过下载: %s", local_path)
            return f"file://{os.path.abspath(local_path)}"

        logger.info("下载图片: %s -> %s", url, local_path)
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)
        return f"file://{os.path.abspath(local_path)}"
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("下载图片失败 (%s): %s", url, e)
        return None


def _read_image_as_base64(local_path: str) -> str | None:
    """读取本地图片文件并返回 base64 编码字符串，失败返回 None。"""
    try:
        with open(local_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("读取本地图片失败 (%s): %s", local_path, e)
        return None


# ===========================================================================
# 反序列化（读词条）
# ===========================================================================

def deserialize_to_segments(raw: str, expire_hours: int = 24) -> list[V11Seg]:
    """
    将词条 JSON 字符串反序列化为 V11Seg 列表，供发送使用。

    图片段处理逻辑：
      - 有本地文件（file 字段为 file:// 路径）且文件存在：
          * 若原始 URL 未过期（cached_at + expire_hours > now），直接用原 URL 发送（更快）
          * 若 URL 已过期或没有原 URL，改用本地文件发送
      - 没有本地文件：退回使用 url 字段
    """
    try:
        segments_data: list[dict] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # 兼容旧版：直接当文本
        logger.debug("词条内容不是 JSON，作为文本处理: %s", raw[:80])
        return [V11Seg.text(str(raw))]

    now = int(time.time())
    result: list[V11Seg] = []

    for seg in segments_data:
        seg_type: str = seg.get("type", "")
        data: dict = seg.get("data", {})

        if seg_type == "text":
            text = data.get("text", "")
            if text:
                result.append(V11Seg.text(text))

        elif seg_type == "image":
            file: str = data.get("file", "")
            url: str = data.get("url", "")
            cached_at: int = data.get("cached_at", 0)

            expire_seconds = expire_hours * 3600
            url_expired = (cached_at == 0) or (now - cached_at >= expire_seconds)

            # 本地文件存在时
            local_path = file[len("file://"):] if file.startswith("file://") else file
            local_exists = bool(local_path) and os.path.isfile(local_path)

            if local_exists:
                if not url_expired and url:
                    # URL 未过期，优先用 URL（发送更快、节省带宽）
                    result.append(V11Seg.image(url))
                else:
                    # URL 已过期或无 URL，用 base64 发送本地文件（兼容 Docker 环境）
                    b64 = _read_image_as_base64(local_path)
                    if b64:
                        result.append(V11Seg.image(f"base64://{b64}"))
                    else:
                        result.append(V11Seg.text("（图片读取失败，请重新编辑词条）"))
            elif url:
                # 没有本地文件，尝试用 URL
                result.append(V11Seg.image(url))
            else:
                result.append(V11Seg.text("（找不到图片，请重新编辑词条）"))

        elif seg_type == "face":
            face_id = data.get("id", 0)
            result.append(V11Seg.face(int(face_id)))

        elif seg_type == "at":
            qq = data.get("qq", "")
            result.append(V11Seg.at(str(qq)))

        else:
            # 其他类型：透传
            try:
                result.append(V11Seg(seg_type, data))
            except Exception:  # pylint: disable=broad-except
                logger.warning("无法还原消息段类型 %s，已跳过", seg_type)

    return result


def build_message(raw: str, expire_hours: int = 24) -> V11Message | None:
    """
    反序列化词条并组装成 V11Message。
    若词条为空则返回 None。
    """
    segs = deserialize_to_segments(raw, expire_hours)
    if not segs:
        return None
    msg = V11Message()
    for seg in segs:
        msg += seg
    return msg
