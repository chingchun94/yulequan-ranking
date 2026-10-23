"""Update data.json from an authorized JSON sales provider.

The initial zero values are placeholders, not verified Weidian counts. This
script deliberately does not scrape Weidian pages or guess private endpoints.
"""
from __future__ import annotations

import json
import html
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import requests
import re
import json
import time
from datetime import datetime
from datetime import datetime, timezone, timedelta

from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"
MAX_RESPONSE_BYTES = 1_000_000
SALES_TEXT_PATTERN = re.compile(r"\d+")


def log(message: str) -> None:
    print(message, file=sys.stderr)

# 1. 初始数据列表
characters_data = [
    {"id":"weizhi","name":"卫枝","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7882013126"},
    {"id":"chuli","name":"初礼","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7881987582"},
    {"id":"tiansanqi","name":"田三七","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7882038552"},
    {"id":"yunweishan","name":"云为衫","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7881985242"},
    {"id":"caiminmin","name":"蔡敏敏","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7882036608"},
    {"id":"linwanxing","name":"林晚星","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7882024882"},
    {"id":"xiaolanhua","name":"小兰花","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7881927436"},
    {"id":"lingmiaomiao","name":"凌妙妙","url":"https://shop1675868235.v.weidian.com/item.html?itemID=7882101684"}
]

def fetch_and_save():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    print(f"开始抓取数据，共 {len(characters_data)} 个页面...")

    for char in characters_data:
        try:
            #print(f"正在抓取 [{char['order']}] {char['name']}...", end=" ", flush=True)
            response = requests.get(char['url'], headers=headers, timeout=10)
            
            if response.status_code == 200:
                # 提取源码中的销量
                #match = re.search(r'"soldText":"销量\s*(\d+)"', response.text)
                #sales_count = int(match.group(1)) if match else 0

                # 修改后的匹配逻辑
                # 兼容 "soldText":"销量 0" 和 &#34;soldText&#34;:&#34;销量 0&#34;
                match = re.search(r'soldText(?:&#34;|"):(?:&#34;|")销量\s*(\d+)', response.text)
                sales_count = int(match.group(1)) if match else 0
                
                char['sales'] = sales_count
                char['salesVerified'] = True
                print(f"完成 (销量: {sales_count})")
            else:
                print(f"失败 (状态码: {response.status_code})")
        except Exception as e:
            print(f"报错: {str(e)}")
        
        # 间隔 1.5 秒
        #time.sleep(1.5)

    # 按 data.json 现有 schema 补全字段，并保留原有排序、销量和图片信息。
    with DATA_FILE.open("r", encoding="utf-8") as stream:
        existing_data = json.load(stream)
    existing_characters = {
        character["id"]: character
        for character in existing_data.get("characters", [])
        if isinstance(character, dict) and isinstance(character.get("id"), str)
    }

    normalized_characters = []
    for index, character in enumerate(characters_data, start=1):
        previous = existing_characters.get(character["id"], {})
        normalized_characters.append({
            "id": character["id"],
            "name": character["name"],
            "order": previous.get("order", index),
            "url": character["url"],
            "image": previous.get("image"),
            "sales": character.get("sales", previous.get("sales", 0)),
            "salesVerified": character.get("salesVerified", previous.get("salesVerified", False)),
        })
    normalized_characters.sort(key=lambda character: character["order"])

    # 构造与 data.json 一致的顶层格式。
    CST = timezone(timedelta(hours=8))  # 固定大陆时间 UTC+8
    final_output = {
        "eventName": existing_data.get("eventName", "鱼了圈海选赛"),
        "schemaVersion": existing_data.get("schemaVersion", 1),
        #"lastUpdated": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        "lastUpdated": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
        "sourceStatus": "verified" if all(item["salesVerified"] for item in normalized_characters) else "partial",
        "sourceNote": existing_data.get("sourceNote", "销量数据来源状态以各角色的 salesVerified 字段为准。"),
        "characters": normalized_characters,
    }

    # 原子写入项目根目录的 data.json。
    atomic_write(final_output)
    
    print("\n✅ 数据抓取完毕！已生成 data.json 文件。")

def fetch_provider(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("SALES_PROVIDER_URL must be an HTTPS URL")
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "YulequanRanking/1.0"})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f"Provider returned HTTP {response.status}")
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("Provider response is too large")
    payload = json.loads(body)
    if not isinstance(payload, dict) or not isinstance(payload.get("sales"), dict):
        raise ValueError("Provider response must be an object with a sales object")
    return payload["sales"]


def parse_sales_value(value: object) -> int | None:
    """Parse an authorized provider value into a nonnegative vote count.

    Accepts an integer, a soldText string (for example ``"Sold 1,234 件"``),
    or an object containing a ``soldText`` field. This function only parses
    content already supplied by the authorized provider; it does not fetch pages.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, dict):
        value = value.get("soldText")
    if not isinstance(value, str):
        return None

    text = html.unescape(value).strip()
    digits = SALES_TEXT_PATTERN.findall(text)
    if not digits:
        return None
    try:
        return int("".join(digits))
    except ValueError:
        return None


def atomic_write(data: dict) -> None:
    fd, temp_name = tempfile.mkstemp(prefix="data.", suffix=".tmp", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, DATA_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


if __name__ == "__main__":
    fetch_and_save()
