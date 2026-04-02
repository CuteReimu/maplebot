import base64
import datetime
import time

import httpx
from nonebot.log import logger

from maplebot.commands.file_utils import (
    load_player_names,
    remove_player_names,
    load_dict,
    save_dict,
    same_dict,
    PLAYER_DICT_FN,
)

PLAYER_URL = "https://www.nexon.com/api/maplestory/no-auth/ranking/v2/na?type=overall&id=legendary&page_index=1&character_name={}"
LEGION_URL = "https://www.nexon.com/api/maplestory/no-auth/ranking/v2/na?type=legion&id=45&page_index=1&character_name={}"
BUFFER_SIZE = 15
SLEEP_PER_REQUEST = 0.5  # seconds


def assert_player_onrank(name):
    url = PLAYER_URL.format(name)
    try:
        response = httpx.get(url, timeout=20)
        data = response.json()
    except Exception as e:
        logger.error(f"Error fetching data for {name}: {e}")
        return True  # Assume online if error occurs

    count = data['totalCount'] if data is not None else 1  # Make no conclusion if error occurs
    return count > 0


def try_request(url, name, retries=3, wait=10):
    data = None
    for retry in range(retries):
        response = None
        try:
            response = httpx.get(url.format(name), timeout=20)
            data = response.json()
            logger.info(f"Requested for {name} successfully")
            break
        except Exception as e:
            status = response.status_code if response is not None else 'N/A'
            logger.warning(f"Error fetching player data for {name}: {e}, retrying ({retry+1}/3)..., request status: {status}")
            if retry == 2:
                logger.warning(f"Fetch is too fast, waiting for {wait} seconds")
                time.sleep(wait)
            continue
    return data


def request_from_name_list():
    names_dict = load_player_names()
    names = list(names_dict.keys())
    names_to_del = []

    for i, name in enumerate(names):
        player_dict = load_dict(PLAYER_DICT_FN.format(name))
        if len(player_dict) == 0:
            player_dict['data'] = []
            player_dict['img'] = ""

        if i % 50 == 0:
            logger.info(f"Processing player {i}...")

        data = try_request(LEGION_URL, name)
        count = data['totalCount'] if data is not None else 0
        if count == 0:
            data = try_request(PLAYER_URL, name)
            count = data['totalCount'] if data is not None else 0

            if count == 0:
                update_time = names_dict[name]
                time_in_days = (
                            datetime.datetime.now() - datetime.datetime.strptime(update_time, "%Y-%m-%d %H:%M:%S")).days
                # names_dict[name] = update_time  # Removed: no-op
                if time_in_days > 3:
                    names_to_del.append(name)
                    del names_dict[name]
                logger.info(f"Player {name} does not exist for {time_in_days} days.")
                time.sleep(SLEEP_PER_REQUEST * 2)  # Avoid hitting rate limits
                continue

        logger.info(f"{name} data found")

        player_name = data['ranks'][0]['characterName']
        exp = data['ranks'][0]['exp']
        lvl = data['ranks'][0]['level']
        img_url = data['ranks'][0]['characterImgURL']
        job_id = data['ranks'][0].get('jobID', -1)
        job_detail = data['ranks'][0].get('jobDetail', -1)
        job_name = data['ranks'][0].get('jobName', '')
        legion_lvl = data['ranks'][0].get('legionLevel', 0)
        legion_raid = data['ranks'][0].get('raidPower', 0)

        try:
            response = httpx.get(img_url, timeout=20)
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

        cur_dict = {
            "name": player_name,
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exp": exp,
            "level": lvl,
            "jobID": job_id,
            "jobDetail": job_detail,
            "jobName": job_name,
            "legionLevel": legion_lvl,
            "raidPower": legion_raid,
        }

        if img64 == '':
            if 'img' not in player_dict:
                player_dict['img'] = ""
        else:
            player_dict['img'] = img64

        last_dict = player_dict['data'][-1] if len(player_dict['data']) > 0 else None
        if last_dict is not None and same_dict(last_dict, cur_dict):
            continue
        player_dict['data'].append(cur_dict)
        player_dict['data'] = sorted(player_dict['data'], key=lambda x: x['datetime'])[-BUFFER_SIZE:]

        save_dict(PLAYER_DICT_FN.format(name), player_dict)
        names_dict[name] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Updated data for player {name}")

        time.sleep(SLEEP_PER_REQUEST)  # Avoid hitting rate limits
    remove_player_names(names_to_del, names_dict)


async def scrape_role_background():
    """后台预抓取角色数据（供 cron 任务调用）"""
    sta = time.time()
    logger.info("Starting data scrape...")
    try:
        request_from_name_list()
    except Exception as e:
        logger.error(f"Data scrape failed: {e}")
        raise
    end = time.time()
    elapsed = (end - sta) / 60
    logger.info(f"Data scrape completed in {elapsed:.2f} minutes")
