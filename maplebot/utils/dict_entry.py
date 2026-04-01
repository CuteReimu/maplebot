"""词条消息的序列化 / 反序列化 + 图片本地缓存管理"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

import httpx
from nonebot.adapters.onebot.v11 import Message as V11Message, MessageSegment as V11Seg
from nonebot.log import logger

# ---- 图片缓存目录（仅用于持久化原始文件，避免重复下载） ----
_CACHE_DIR = "chat_images"
os.makedirs(_CACHE_DIR, exist_ok=True)


# ===========================================================================
# 序列化（存词条）
# ===========================================================================

def serialize_message(msg: V11Message) -> str:
    """
    将 OneBot V11 Message 序列化为 JSON 字符串存入词条数据库。

    图片段：下载原图到本地 chat_images/ 缓存，JSON 中只存本地文件路径。
    文本段：直接保留 text。
    其他段：保留原始结构。
    """
    segments: list[dict[str, Any]] = []
    for seg in msg:
        seg_type: str = seg.type
        data: dict = dict(seg.data)

        if seg_type == "image":
            # 优先取 url，其次取 file
            url: str = data.get("url", "") or data.get("file", "")
            local_path = _download_image(url) if url else None
            if local_path:
                segments.append({"type": "image", "data": {"file": local_path}})
            else:
                logger.warning("图片段无法获取内容，已跳过: %s", data)
        else:
            segments.append({"type": seg_type, "data": data})

    return json.dumps(segments, ensure_ascii=False)


def _download_image(url: str) -> str | None:
    """
    下载图片到 chat_images/ 本地缓存，返回本地文件路径。
    若 url 是 file:// 本地路径则直接返回该路径。
    下载失败返回 None。
    """
    # 本地文件路径
    local_path = url[len("file://"):] if url.startswith("file://") else None
    if local_path and os.path.isfile(local_path):
        return local_path

    # 普通 URL：先查本地缓存
    try:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        url_path = url.split("?")[0].rstrip("/")
        ext = os.path.splitext(url_path)[1]
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
            ext = ".jpg"
        cached = os.path.join(_CACHE_DIR, f"{url_hash}{ext}")

        if not os.path.exists(cached):
            logger.info("下载图片: %s -> %s", url, cached)
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                with open(cached, "wb") as f:
                    f.write(resp.content)

        return cached
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("获取图片失败 (%s): %s", url, e)
        return None


def _read_file_base64(path: str) -> str | None:
    """读取文件并返回 base64 字符串，失败返回 None。"""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("读取文件失败 (%s): %s", path, e)
        return None


# ===========================================================================
# 反序列化（读词条）
# ===========================================================================

def deserialize_to_segments(raw: str) -> list[V11Seg]:
    """
    将词条 JSON 字符串反序列化为 V11Seg 列表，供发送使用。

    图片段：直接取 base64 字段，通过 base64:// 协议发送，兼容 Docker 环境。
    expire_hours 参数保留以兼容调用方，实际不再使用。
    """
    try:
        segments_data: list[dict] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # 兼容旧版：直接当文本
        logger.debug("词条内容不是 JSON，作为文本处理: %s", raw[:80])
        return [V11Seg.text(str(raw))]

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
            # 去掉 file:// 前缀（兼容旧格式）
            local_path = file[len("file://"):] if file.startswith("file://") else file

            b64: str = ""
            if local_path and os.path.isfile(local_path):
                b64 = _read_file_base64(local_path) or ""

            # 兼容旧格式：有 url 字段，重新下载到本地再转 base64
            if not b64:
                url: str = data.get("url", "")
                if url:
                    dl = _download_image(url)
                    if dl:
                        b64 = _read_file_base64(dl) or ""

            if b64:
                result.append(V11Seg.image(f"base64://{b64}"))
            else:
                result.append(V11Seg.text("（找不到图片，请重新编辑词条）"))

        elif seg_type == "face":
            result.append(V11Seg.face(int(data.get("id", 0))))

        elif seg_type == "at":
            result.append(V11Seg.at(str(data.get("qq", ""))))

        else:
            try:
                result.append(V11Seg(seg_type, data))
            except Exception:  # pylint: disable=broad-except
                logger.warning("无法还原消息段类型 %s，已跳过", seg_type)

    return result


def build_message(raw: str) -> V11Message | None:
    """
    反序列化词条并组装成 V11Message。
    若词条为空则返回 None。
    """
    segs = deserialize_to_segments(raw)
    if not segs:
        return None
    msg = V11Message()
    for seg in segs:
        msg += seg
    return msg
