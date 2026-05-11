import datetime
import base64
import json
import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from nonebot.log import logger

from maplebot.commands.scrape import try_request, BUFFER_SIZE


# ---------- AES解密 ----------
def decrypt_data(base64_string: str) -> dict:
    key = b'0081a87cab06abc65de027850c191f16'

    decoded = json.loads(base64.b64decode(base64_string))
    iv = bytes.fromhex(decoded['iv'])
    ciphertext = bytes.fromhex(decoded['encrypted'])

    cipher = AES.new(key[:32], AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)

    return json.loads(decrypted)


# ---------- 获取在线角色数据 ----------
async def get_online_characters(character_name: str, sever: str = "NA") -> dict | None:
    url = f"https://maplebot.io/api/character/{character_name}?region={sever}"
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh-TW;q=0.7,zh;q=0.6',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://maplebot.io/character/PoorShack?region=NA',
        'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        # 'cookie': '_ga=GA1.1.1277652103.1778089711; _ga_HBSDFV7RPL=GS2.1.s1778320953$o2$g1$t1778321012$j1$l0$h0',
    }

    return await try_request(url, None, headers=headers)


# ---------- 整理数据 ----------
async def process_character_data(data: dict) -> dict | None:
    try:
        if data is None or 'encrypted' not in data:
            return None
        json_data = decrypt_data(data['encrypted'])
        if not json_data or 'data' not in json_data:
            return None

        player_dict = None
        character = json_data['data']['character']
        name = character['name']
        job = character['job']
        img_url = character['imageUrl']
        img_url = f"https://cdn.maplebot.io{img_url}"
        exp_history = json_data['data']['expHistory'][-BUFFER_SIZE:]
        legion = character.get('legion', {}).get('level', 0)
        img = await get_character_img(img_url, name)
        player_dict = {'data': [], 'img': img}
        for _, exp in enumerate(exp_history):
            date = exp['date']
            total_exp = exp['totalExp']
            level = exp['level']
            player_dict['data'].append(
                {
                    "name": name,
                    "datetime": datetime.datetime.fromisoformat(date).strftime("%Y-%m-%d"),
                    "exp": int(total_exp),
                    "level": int(level),
                    "jobName": job,
                    "legionLevel": int(legion),
                }
            )
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        player_dict = None
        logger.error(f"Error processing character {name} online, exception: {e}")

    return player_dict


# ---------- 通过url下载图片到base64 ----------
async def get_character_img(img_url: str, player_name: str = None) -> str:
    img64 = ""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(img_url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch image, status: {response.status_code}")
        if response.headers.get('Content-Type', '').startswith('image/'):
            img64 = base64.b64encode(response.content).decode('utf-8')
        else:
            img64 = ""
            content_type = response.headers.get('Content-Type', 'N/A')
            logger.warning(f"URL for {player_name} does not point to an image, content type: {content_type}")
    except Exception as e:
        img64 = ""
        logger.warning(f"Error fetching image for {player_name}: {e}")
    return img64


def covert_total_exp_to_level_exp(player_dict, lvl_culm):
    for entry in player_dict['data']:
        total_exp = entry['exp']
        level = entry['level']
        exp_for_current_level = total_exp - lvl_culm.get(str(level), 0)
        entry['exp'] = exp_for_current_level
