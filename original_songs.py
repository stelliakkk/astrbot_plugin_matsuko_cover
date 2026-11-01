"""Select and deliver the exact original recording without voice conversion."""

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

from astrbot.api import logger

from .api import QQMusicAPI


def command_keyword(message: str) -> str:
    """Remove just the leading command, preserving spaces inside the song title."""
    parts = message.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


async def _run_audio_tool(*args: str) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=120)
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.communicate()
        raise
    if process.returncode:
        raise RuntimeError("音频格式检查或转换失败，请换一首歌重试。")
    return stdout


async def ensure_mp3(source: Path, ffmpeg_path: str) -> Path:
    """Keep MP3 bytes intact, converting other audio formats to a real MP3."""
    ffmpeg = Path(ffmpeg_path) if ffmpeg_path else Path(shutil.which("ffmpeg") or "")
    if not ffmpeg.is_file():
        raise RuntimeError("未找到 FFmpeg，请检查插件的原曲音频工具路径。")
    ffprobe = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix == ".exe" else "ffprobe")
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise RuntimeError("未找到 FFmpeg/FFprobe，请检查插件的原曲音频工具路径。")
    metadata = json.loads(
        await _run_audio_tool(
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name:format=format_name",
            "-of",
            "json",
            str(source),
        )
    )
    streams = metadata.get("streams", [])
    if not streams:
        raise RuntimeError("下载结果没有有效音轨，请换一首歌重试。")
    destination = source.with_suffix(".mp3")
    if destination == source:
        destination = source.with_name(source.stem + "_original.mp3")
    try:
        if (
            streams[0].get("codec_name") == "mp3"
            and metadata.get("format", {}).get("format_name") == "mp3"
        ):
            shutil.copyfile(source, destination)
        else:
            await _run_audio_tool(
                str(ffmpeg),
                "-v",
                "error",
                "-nostdin",
                "-y",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-vn",
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(destination),
            )
        if not destination.is_file() or destination.stat().st_size == 0:
            raise RuntimeError("未生成有效的 MP3 文件。")
        return destination
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


async def inspect_audio(source: Path, ffmpeg_path: str) -> dict:
    """Read the actual stream/container without trusting the downloaded suffix."""
    ffmpeg = Path(ffmpeg_path) if ffmpeg_path else Path(shutil.which("ffmpeg") or "")
    if not ffmpeg.is_file():
        raise RuntimeError("未找到 FFmpeg，请检查插件的原曲音频工具路径。")
    ffprobe = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix == ".exe" else "ffprobe")
    metadata = json.loads(
        await _run_audio_tool(
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,bits_per_raw_sample:format=format_name,bit_rate",
            "-of",
            "json",
            str(source),
        )
    )
    if (
        not metadata.get("streams")
        or int(metadata["streams"][0].get("sample_rate") or 0) <= 0
        or int(metadata["streams"][0].get("channels") or 0) <= 0
    ):
        raise RuntimeError("下载结果没有有效音轨。")
    return metadata


async def prepare_original_audio(source: Path, ffmpeg_path: str) -> Path:
    """Preserve native FLAC/MP3/OGG/AAC bytes with an accurate extension."""
    metadata = await inspect_audio(source, ffmpeg_path)
    codec = metadata["streams"][0].get("codec_name")
    container = metadata.get("format", {}).get("format_name", "")
    extension = None
    if codec == "flac" and container == "flac":
        extension = ".flac"
    elif codec == "mp3" and container == "mp3":
        extension = ".mp3"
    elif codec in {"vorbis", "opus"} and container == "ogg":
        extension = ".ogg"
    elif codec == "aac" and "mp4" in container:
        extension = ".m4a"
    elif codec == "aac" and container == "aac":
        extension = ".aac"
    if extension is None:
        raise RuntimeError("原曲格式暂不支持，请换个版本重试。")
    destination = source.with_suffix(extension)
    if source != destination:
        source.replace(destination)
    return destination


async def download_qq_song(plugin, api, songmid: str, song_name: str) -> str | None:
    """Try authorized high-quality sources first, including download fallbacks."""
    attempts = (
        max(1, int(plugin.qqmusic_retry_max_attempts))
        if plugin.qqmusic_retry_on_ratelimit
        else 1
    )
    sources = []
    for attempt in range(attempts):
        try:
            sources = await asyncio.wait_for(
                api.fetch_song_sources(songmid), timeout=plugin.music_api_timeout
            )
            if sources:
                break
        except Exception as exc:
            logger.warning("QQ Music quality lookup failed: %s", type(exc).__name__)
        if attempt + 1 < attempts:
            await asyncio.sleep(5)
    for source in sources:
        path = await plugin._download_audio(
            source.url, source.extension, max_size_mb=plugin.max_song_audio_size_mb
        )
        if not path:
            continue
        try:
            if plugin.original_song_ffmpeg_path or shutil.which("ffmpeg"):
                await inspect_audio(Path(path), plugin.original_song_ffmpeg_path)
            logger.info("QQ Music downloaded quality: %s", source.quality)
            return path
        except Exception as exc:
            logger.warning(
                "QQ Music audio unavailable at quality %s: %s",
                source.quality,
                type(exc).__name__,
            )
            Path(path).unlink(missing_ok=True)
    return None


async def send_original_song(plugin, event, *, as_file: bool = False) -> None:
    """Search, wait for a selection, and send only the requested original audio."""
    command = "听歌文件" if as_file else "听歌"
    keyword = command_keyword(event.message_str)
    if not keyword:
        await event.send(
            event.plain_result(f"用法：/{command} <歌名或歌手>\n例如：/{command} 晴天")
        )
        return
    key = f"{event.unified_msg_origin}:{event.get_sender_id()}"
    if key in plugin._original_song_requests:
        await event.send(
            event.plain_result("你已有听歌请求，请先完成选择或等待音频发送。")
        )
        return
    plugin._original_song_requests.add(key)
    source = None
    audio = None
    api = QQMusicAPI()
    try:
        songs = await asyncio.wait_for(
            api.fetch_data(keyword=keyword, limit=10), timeout=plugin.music_api_timeout
        )
        if not songs:
            await event.send(
                event.plain_result("没有搜到歌曲，请换个歌名或加上歌手重试。")
            )
            return
        choices = [
            f"{song['name']} - {song['artists']}"
            + (f" · {song['album']}" if song.get("album") else "")
            for song in songs
        ]
        selected, event = await plugin.selection_ui.choose(
            event,
            f"🎵 选择原曲 · {'最高音质文件' if as_file else '语音播放'}\n来源：QQ 音乐",
            choices,
            plugin.timeout,
        )
        if selected is None:
            return
        song = songs[selected]
        downloaded = await download_qq_song(plugin, api, song["songmid"], song["name"])
        if not downloaded:
            await event.send(
                event.plain_result(
                    "这首歌暂无可下载的音源，可能与播放权限、网络或大小限制有关，请换个版本重试。"
                )
            )
            return
        source = Path(downloaded)
        audio = await prepare_original_audio(source, plugin.original_song_ffmpeg_path)
        await plugin._send_cover_result(
            event,
            str(audio),
            song_name=f"{song['name']} - {song['artists']}",
            delivery="file" if as_file else "voice",
        )
    except TimeoutError:
        await event.send(event.plain_result("听歌请求超时，请重新发送命令再试。"))
    except ValueError as exc:
        await event.send(event.plain_result(str(exc)))
    except Exception as exc:
        logger.error(
            "[MatsukoCover] Original song request failed: %s", type(exc).__name__
        )
        await event.send(event.plain_result("原曲处理或发送失败，请稍后重试。"))
    finally:
        try:
            await api.close()
        finally:
            plugin._original_song_requests.discard(key)
            for path in {source, audio} - {None}:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    logger.debug("[MatsukoCover] Original audio cleanup deferred")
