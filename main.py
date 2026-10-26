import asyncio
import json
import logging
import math
import re
import time
from collections import OrderedDict
from urllib.parse import urlencode, urlsplit

import aiohttp
from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star, register

logger = logging.getLogger(__name__)

API_BASE = "https://api.nekosapi.com/v4"
USER_AGENT = "AstrBotRandomIllustration/1.1 (safe-tag-mode)"
CATEGORIES = {
    "waifu": "动漫少女",
    "neko": "猫娘",
    "kitsune": "狐娘",
    "husbando": "动漫少年",
}
ALIASES = {
    "少女": "waifu", "动漫少女": "waifu",
    "猫娘": "neko", "狐娘": "kitsune",
    "少年": "husbando", "动漫少年": "husbando",
}
TAG_LABELS = {
    "waifu": "动漫少女",
    "husbando": "动漫少年",
    "neko": "猫娘",
    "kitsune": "狐娘",
    "cat_ears": "猫耳",
    "fox_ears": "狐耳",
    "rabbit_ears": "兔耳",
    "animal_ears": "兽耳",
    "cute": "可爱",
    "boy": "男孩",
    "bishounen": "美少年",
    "angel": "天使",
    "demon": "恶魔",
    "magical_girl": "魔法少女",
    "princess": "公主",
    "knight": "骑士",
    "maid": "女仆",
    "butler": "执事",
    "idol": "偶像",
    "miko": "巫女",
    "nun": "修女",
    "vampire": "吸血鬼",
    "elf": "精灵",
    "dragon_girl": "龙娘",
    "glasses": "眼镜",
    "twintails": "双马尾",
    "ponytail": "马尾",
    "short_hair": "短发",
    "long_hair": "长发",
    "silver_hair": "银发",
    "blonde_hair": "金发",
    "black_hair": "黑发",
    "red_eyes": "红瞳",
    "blue_eyes": "蓝瞳",
    "green_eyes": "绿瞳",
    "heterochromia": "异色瞳",
    "ahoge": "呆毛",
    "wings": "翅膀",
    "tail": "尾巴",
    "horns": "角",
    "kimono": "和服",
    "yukata": "浴衣",
    "school_uniform": "制服",
    "serafuku": "水手服",
    "dress": "连衣裙",
    "hat": "帽子",
    "scarf": "围巾",
    "gloves": "手套",
    "thighhighs": "过膝袜",
    "swimsuit": "泳装",
    "sky": "天空",
    "cloud": "云",
    "ocean": "海",
    "mountain": "山",
    "forest": "森林",
    "flower": "花",
    "cherry_blossoms": "樱花",
    "starry_sky": "星空",
    "sunset": "夕阳",
    "night": "夜晚",
    "rain": "雨",
    "snow": "雪",
    "city": "城市",
    "indoors": "房间",
    "cafe": "咖啡店",
    "classroom": "教室",
    "library": "图书馆",
    "train": "电车",
    "station": "车站",
    "shrine": "神社",
    "festival": "祭典",
    "fireworks": "烟花",
    "beach": "海边",
    "garden": "庭院",
    "ruins": "废墟",
    "light": "光",
    "shadow": "影",
    "cat": "猫",
    "dog": "狗",
    "rabbit": "兔子",
    "fox": "狐狸",
    "bird": "鸟",
    "fish": "鱼",
    "panda": "熊猫",
    "deer": "鹿",
    "horse": "马",
    "wolf": "狼",
    "cake": "蛋糕",
    "sweets": "甜点",
    "coffee": "咖啡",
    "tea": "红茶",
    "bread": "面包",
    "ramen": "拉面",
    "sushi": "寿司",
    "fruit": "水果",
    "ice_cream": "冰淇淋",
    "bento": "便当",
    "watercolor": "水彩",
    "impasto": "厚涂",
    "lineart": "线稿",
    "monochrome": "单色",
    "chibi": "Q版",
    "pixel_art": "像素画",
    "3d": "3DCG",
    "pencil": "铅笔",
    "traditional_media": "手绘",
    "background": "背景",
    "valentine": "情人节",
    "christmas": "圣诞节",
    "halloween": "万圣节",
    "new_year": "新年",
    "birthday": "生日",
    "summer_festival": "夏日祭",
    "sports_festival": "体育祭",
    "graduation": "毕业",
    "fantasy": "幻想",
    "slice_of_life": "日常",
    "healing": "治愈",
    "heartwarming": "温馨",
    "comedy": "搞笑",
    "science_fiction": "科幻",
    "music": "音乐",
    "dance": "舞蹈",
    "sports": "运动",
    "bouquet": "花束",
    "umbrella": "伞",
    "book": "书",
    "clock": "时钟",
    "balloon": "气球",
    "present": "礼物",
    "letter": "信件",
    "camera": "相机",
    "original": "原创",
    "illustration": "插画",
    "scenery": "风景",
    "portrait": "肖像",
}
TAG_ALIASES = {label: key for key, label in TAG_LABELS.items()}
TAG_HELP = "可用标签（直接写在 /插画 后面即可筛选）：\n" + "\n".join(
    f"{key}：{label}" for key, label in TAG_LABELS.items()
)
NUMBERS = dict(zip("一二三四五六七八九十", range(1, 11)))
HELP = (
    "全年龄随机插画\n"
    "/插画 —— 随机一张\n"
    "/插画 3 猫娘 —— 三张猫娘插画\n"
    "/插画 狐娘 二张 —— 两张狐娘插画\n"
    "/插画标签 —— 查看完整标签词典\n"
    "分类标签：少女 / 猫娘 / 狐娘 / 少年\n"
    "标签示例：女仆 / 银发 / 猫耳 / 海边 / 水彩\n"
    "英文标签也可以直接使用，例如 maid / silver_hair / cat_ears。\n"
    "也可以使用 /随机插画；分类与数量可交换顺序。\n"
    "当前图片源仅支持分类筛选，不支持这些细粒度标签筛选。"
)


class FetchError(Exception):
    pass


def bounded_int(config, key, default, lower, upper):
    try:
        value = int(config.get(key, default))
    except (TypeError, ValueError, OverflowError):
        value = default
    return max(lower, min(upper, value))


def parse_request(arguments, default_category, max_count):
    count = 1
    selector = default_category
    has_count = False
    has_selector = False
    for token in arguments:
        if not token:
            continue
        match = re.fullmatch(r"([0-9]+|[一二三四五六七八九十])(?:张|份)?", token)
        if match:
            if has_count:
                raise ValueError("数量只能填写一次。")
            number = match.group(1)
            count = NUMBERS[number] if number in NUMBERS else int(number)
            has_count = True
        else:
            normalized = token.lower()
            resolved = ALIASES.get(normalized, normalized)
            if resolved not in TAG_LABELS:
                resolved = TAG_ALIASES.get(token)
            if resolved not in TAG_LABELS:
                raise ValueError("不支持这个标签。发送 /插画帮助 查看用法。")
            if has_selector:
                raise ValueError("每次只能选择一个标签。")
            selector = resolved
            has_selector = True
    if not 1 <= count <= max_count:
        raise ValueError(f"每次可以获取 1～{max_count} 张插画。")
    return count, selector


def validate_image_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "https"
            and parsed.netloc == "cdn.nekosapi.com"
            and parsed.query == ""
            and parsed.fragment == ""
            and re.fullmatch(
                r"/nekos-api/images/[a-zA-Z0-9_/-]+\.(?:webp|png|jpe?g|gif)",
                parsed.path,
            ) is not None
        )
    except ValueError:
        return False


def validate_image_bytes(data):
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"GIF87a")
        or data.startswith(b"GIF89a")
        or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")
    )


@register(
    "astrbot_plugin_random_illustration",
    "Local",
    "全年龄随机动漫插画，支持标签、数量和用户冷却",
    "1.1.0",
)
class RandomIllustrationPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._session = None
        self._busy = set()
        self._cooldowns = OrderedDict()
        self._slots = asyncio.Semaphore(3)

    def _client(self):
        if self._session is None or self._session.closed:
            timeout = bounded_int(self.config, "timeout_seconds", 25, 5, 120)
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": USER_AGENT},
                connector=aiohttp.TCPConnector(limit=6),
                trust_env=True,
            )
        return self._session

    async def _get(self, url, limit, image=False):
        retries = bounded_int(self.config, "retries", 2, 0, 3)
        for attempt in range(retries + 1):
            delay = min(2 ** attempt, 5)
            try:
                async with self._client().get(url, allow_redirects=False) as response:
                    if response.status != 200:
                        retryable = response.status == 429 or response.status >= 500
                        if not retryable or attempt == retries:
                            raise FetchError(f"图片服务暂时不可用（HTTP {response.status}）。")
                        retry_after = response.headers.get("Retry-After", "")
                        if retry_after.isdigit():
                            delay = min(max(int(retry_after), delay), 10)
                    else:
                        content_type = response.headers.get("Content-Type", "").lower()
                        if image and not content_type.startswith("image/"):
                            raise FetchError("图片服务返回的格式不正确。")
                        if response.content_length is not None and response.content_length > limit:
                            raise FetchError("图片或接口响应超过大小限制。")
                        buffer = bytearray()
                        async for chunk in response.content.iter_chunked(65536):
                            buffer.extend(chunk)
                            if len(buffer) > limit:
                                raise FetchError("图片或接口响应超过大小限制。")
                        if not buffer:
                            raise FetchError("图片服务返回了空内容。")
                        return bytes(buffer)
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt == retries:
                    raise FetchError("连接图片服务失败或超时，请稍后重试。") from exc
            await asyncio.sleep(delay)
        raise FetchError("图片获取失败。")

    async def _metadata(self, tag, count):
        query = urlencode({"limit": count, "tags": tag, "rating": "safe"})
        body = await self._get(f"{API_BASE}/images?{query}", 65536)
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise FetchError("图片服务返回了无效数据。") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise FetchError("图片服务返回了无效数据。")
        records = []
        seen = set()
        for record in payload["items"]:
            if not isinstance(record, dict):
                continue
            url = record.get("url")
            if validate_image_url(url) and url not in seen:
                records.append(record)
                seen.add(url)
            if len(records) == count:
                break
        if not records:
            raise FetchError(f"标签“{TAG_LABELS.get(tag, tag)}”暂无安全插画。")
        return records

    def _credit(self, record):
        artist = str(record.get("artist_name") or "未知")[:100]
        source = record.get("source_url")
        tags = record.get("tags")
        tag_text = ", ".join(str(tag) for tag in tags[:8]) if isinstance(tags, list) else ""
        credit = f"\n画师：{artist} | 图片来源：Nekos API"
        if tag_text:
            credit += f"\n标签：{tag_text}"
        if isinstance(source, str) and source.startswith("https://"):
            credit += f"\n原作：{source[:500]}"
        return credit

    @filter.command("插画", alias={"随机插画"})
    async def illustration(
        self, event: AstrMessageEvent, first: str = "", second: str = ""
    ):
        if first.lower() in {"帮助", "help", "?"}:
            yield event.plain_result(HELP)
            return
        max_count = bounded_int(self.config, "max_count", 3, 1, 5)
        default = str(self.config.get("default_category", "waifu"))
        if default not in TAG_LABELS:
            default = "waifu"
        try:
            count, tag = parse_request((first, second), default, max_count)
        except ValueError as exc:
            yield event.plain_result(str(exc))
            return

        key = (str(event.unified_msg_origin), str(event.get_sender_id()))
        now = time.monotonic()
        for expired_key, expiry in list(self._cooldowns.items()):
            if expiry <= now:
                self._cooldowns.pop(expired_key, None)
        if key in self._busy:
            yield event.plain_result("上一条插画请求还在处理中。")
            return
        remaining = self._cooldowns.get(key, 0) - now
        if remaining > 0:
            yield event.plain_result(f"请再等 {math.ceil(remaining)} 秒。")
            return
        if self._slots.locked():
            yield event.plain_result("当前请求较多，请稍后再试。")
            return

        self._busy.add(key)
        cooldown = bounded_int(self.config, "cooldown_seconds", 10, 0, 3600)
        self._cooldowns[key] = now + cooldown
        while len(self._cooldowns) > 4096:
            self._cooldowns.popitem(last=False)
        sent = 0
        failure = None
        try:
            async with self._slots:
                records = await self._metadata(tag, count)
                limit = bounded_int(self.config, "max_image_mb", 10, 1, 20) * 1024 * 1024
                for record in records:
                    try:
                        data = await self._get(record["url"], limit, image=True)
                        if not validate_image_bytes(data):
                            raise FetchError("图片文件格式校验失败。")
                        components = [Image.fromBytes(data)]
                        if self.config.get("show_credit", True):
                            components.append(Plain(text=self._credit(record)))
                        await event.send(event.chain_result(components))
                        sent += 1
                    except FetchError as exc:
                        logger.warning("Random illustration fetch failed: %s", exc)
                        failure = str(exc)
                    except Exception:
                        logger.exception("Random illustration send failed")
                        failure = "发送失败，请检查 Bot 平台连接和图片发送权限。"
        except FetchError as exc:
            logger.warning("Random illustration service failed: %s", exc)
            failure = str(exc)
        except Exception:
            logger.exception("Random illustration request failed")
            failure = "插画请求失败，请检查 AstrBot 日志。"
        finally:
            self._busy.discard(key)

        if sent < count:
            detail = failure or "图片服务本次返回的图片数量不足。"
            yield event.plain_result(f"已发送 {sent}/{count} 张。{detail}")

    @filter.command("插画标签", alias={"随机插画标签"})
    async def illustration_tags(self, event: AstrMessageEvent):
        yield event.plain_result(TAG_HELP)

    async def terminate(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()
