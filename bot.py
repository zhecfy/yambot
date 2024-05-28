import os
import sys

bot_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(bot_dir)
sys.path.append("Yoku")

import argparse
import logging
from typing import Tuple, List
from datetime import datetime

from mercari.mercari.mercari import MercariSort, MercariOrder, MercariSearchStatus, Item
from mercari.mercari.mercari import search as search_mercari

from Yoku.yoku.consts import KEY_TITLE, KEY_IMAGE, KEY_URL, KEY_POST_TIMESTAMP, KEY_END_TIMESTAMP, KEY_START_TIMESTAMP, KEY_ITEM_ID, KEY_BUYNOW_PRICE, KEY_CURRENT_PRICE, KEY_START_PRICE, KEY_BID_COUNT
from Yoku.yoku.scrape import search as search_yahoo_auctions

from email_utils import EmailConfig, send_tracking_email, prettify
from json_utils import load_file_to_json, save_json_to_file
from config import *

mercari_level_help = """
Yambot's Ambiguity Levels for Mercari
- Level 1 (Absolutely Unique): track all items
- Level 2 (Unique): track items with full keyword in their title
- Level 3 (Ambiguous): search with supplemental keywords, track items with full keyword in their title
"""

mercari_category_help = f"""
Category of Mercari Items
Set the カテゴリー and the number after category_id= in the URL.
CD: {MERCARI_CATEGORY_CD}
List of integers, seperated with comma. Example: 694,695
"""

yahoo_auctions_category_help = f"""
Category of Yahoo! Auctions Items
Set the カテゴリ and the number after auccat= in the URL.
Music: {YAHOO_CATEGORY_MUSIC}
One integer.
"""

mercari_condition_help = """
Conditions of Mercari Items
- 1: 新品、未使用
- 2: 未使用に近い
- 3: 目立った傷や汚れなし
- 4: やや傷や汚れあり
- 5: 傷や汚れあり
- 6: 全体的に状態が悪い
List of integers, seperated with comma. Example: 3,4,6
"""

yahoo_auctions_condition_help = """
Conditions of Yahoo! Auctions Items
- 1: 未使用
- 2: 中古
- 3: 未使用に近い
- 4: 目立った傷や汚れなし
- 5: やや傷や汚れあり
- 6: 傷や汚れあり
- 7: 全体的に状態が悪い
List of integers, seperated with comma. Example: 3,4,6
Note: 2 is equivalent to 3,4,5,6,7
"""

def update(entry: dict) -> Tuple[bool, List]:
    if "site" not in entry or entry["site"] == SITE_MERCARI: # for backwards compatibility
        if entry["level"] == LEVEL_ABSOLUTELY_UNIQUE or entry["level"] == LEVEL_UNIQUE:
            search_keyword = entry["keyword"]
        elif entry["level"] == LEVEL_AMBIGUOUS:
            search_keyword = entry["keyword"] + " " + entry["supplement"]
        else:
            raise ValueError("unknown level")

        # optional parameters
        # TODO: Use blacklist instead of whitelist
        exclude_keyword = ""
        if "exclude_keyword" in entry:
            exclude_keyword = entry["exclude_keyword"]
        category_id = []
        if "category_id" in entry:
            if isinstance(entry["category_id"], int): # backwards compatibility, used to use int
                if entry["category_id"] != 0: # [0] works somehow but better check
                    category_id = [entry["category_id"]]
            else:
                category_id = entry["category_id"]
        price_max = 0
        if "price_max" in entry:
            price_max = entry["price_max"]
        price_min = 0
        if "price_min" in entry:
            price_min = entry["price_min"]
        item_condition_id = []
        if "item_condition_id" in entry:
            item_condition_id = entry["item_condition_id"]

        success, search_result = search_mercari(keywords=search_keyword,
                                                exclude_keywords=exclude_keyword,
                                                sort=MercariSort.SORT_SCORE,
                                                order=MercariOrder.ORDER_DESC,
                                                status=MercariSearchStatus.DEFAULT,
                                                category_id=category_id,
                                                price_max=price_max,
                                                price_min=price_min,
                                                item_condition_id=item_condition_id,
                                                request_interval=REQUEST_INTERVAL)
        
        if not success:
            return False, []

        if entry["level"] == LEVEL_ABSOLUTELY_UNIQUE:
            filtered_search_result = search_result
        elif entry["level"] == LEVEL_UNIQUE or entry["level"] == LEVEL_AMBIGUOUS:
            filtered_search_result = []
            for item in search_result:
                if entry["keyword"].lower() in item.productName.lower():
                    filtered_search_result.append(item)
        
        return True, filtered_search_result
    elif entry["site"] == SITE_YAHOO_AUCTIONS:

        not_parameter_keys = ["id", "site", "last_result", "last_time"]
        parameters = {key: entry[key] for key in entry if key not in not_parameter_keys}

        if "auccat" in parameters and parameters["auccat"] == 0: # backwards compatibility
            parameters.pop("auccat")

        search_result = search_yahoo_auctions(parameters, request_interval=REQUEST_INTERVAL)

        # assume yahoo auction searches always succeed
        # TODO: handle connection errors here
        return True, search_result
    else:
        raise ValueError("unknown site")

def add():
    # 1. read current track.json
    track_json = load_file_to_json(file_path=RESULT_PATH)
    if track_json == None:
        track_json = []

    max_entry_id = 0
    for track_entry in track_json:
        max_entry_id = max(max_entry_id, track_entry["id"])
    
    # 2. interactively add keyword
    new_entry = {}

    # id (unique)
    new_entry["id"] = max_entry_id + 1

    # site
    while True:
        site = input(f"site ('m' for {SITE_MERCARI}, 'y' for {SITE_YAHOO_AUCTIONS}): ")
        if site == "m":
            new_entry["site"] = SITE_MERCARI
            break
        elif site == "y":
            new_entry["site"] = SITE_YAHOO_AUCTIONS
            break
        else:
            print("site error")
            continue

    # search keyword
    # keyword (mercari) or p (yahoo_auctions)
    if new_entry["site"] == SITE_MERCARI:
        new_entry["keyword"] = input("search keyword: ")
    elif new_entry["site"] == SITE_YAHOO_AUCTIONS:
        new_entry["p"] = input("search keyword: ")

    # ambiguity level (mercari only)
    if new_entry["site"] == SITE_MERCARI:
        while True:
            print(mercari_level_help)
            level = int(input("keyword's ambiguity level: "))
            if level == LEVEL_ABSOLUTELY_UNIQUE or level == LEVEL_UNIQUE:
                new_entry["level"] = level
                break
            elif level == LEVEL_AMBIGUOUS:
                new_entry["level"] = level
                new_entry["supplement"] = input("supplemental keyword: ")
                break
            else:
                print("level error")
                continue
    
    # category, optional
    # category_id (mercari) or auccat (yahoo_auctions)
    if new_entry["site"] == SITE_MERCARI:
        print(mercari_category_help)
        input_str = input(f"category (category_id) of items, press enter to skip: ")
        if input_str != "":
            new_entry["category_id"] = list(map(int, input_str.split(',')))
    elif new_entry["site"] == SITE_YAHOO_AUCTIONS:
        print(yahoo_auctions_category_help)
        input_str = input(f"category (auccat) of items, press enter to skip: ")
        if input_str != "":
            new_entry["auccat"] = int(input_str)

    # condition (new or used, etc.), optional
    # item_condition_id (mercari) or istatus (yahoo_auctions)
    if new_entry["site"] == SITE_MERCARI:
        print(mercari_condition_help)
        input_str = input("condition (item_condition_id) of items, press enter to skip: ")
        if input_str != "":
            new_entry["item_condition_id"] = list(map(int, input_str.split(',')))
    elif new_entry["site"] == SITE_YAHOO_AUCTIONS:
        print(yahoo_auctions_condition_help)
        input_str = input("condition (istatus) of items, press enter to skip: ")
        if input_str != "":
            new_entry["istatus"] = list(map(int, input_str.split(',')))

    # maximum price, optional
    # price_max (mercari) or aucmaxprice (yahoo_auctions)
    if new_entry["site"] == SITE_MERCARI:
        input_str = input("maximum price (price_max) of items, press enter to skip: ")
        if input_str != "":
            new_entry["price_max"] = int(input_str)
    elif new_entry["site"] == SITE_YAHOO_AUCTIONS:
        input_str = input("maximum price (aucmaxprice) of items, press enter to skip: ")
        if input_str != "":
            new_entry["aucmaxprice"] = int(input_str)

    # minimum price, optional
    # price_min (mercari only)
    if new_entry["site"] == SITE_MERCARI:
        input_str = input("minimum price (price_min) of items, press enter to skip: ")
        if input_str != "":
            new_entry["price_min"] = int(input_str)
    
    # 3. initial update
    success, search_result = update(new_entry)
    if not success:
        print("initial update failed, abort")
        return
    search_result_dict = {}
    if new_entry["site"] == SITE_MERCARI:
        for item in search_result:
            search_result_dict[item.id] = {"price": item.price, "status": item.status}
    elif new_entry["site"] == SITE_YAHOO_AUCTIONS:
        for item in search_result:
            search_result_dict[item[KEY_ITEM_ID]] = {KEY_CURRENT_PRICE: item[KEY_CURRENT_PRICE], KEY_BID_COUNT: item[KEY_BID_COUNT]}
    new_entry["last_result"] = search_result_dict
    new_entry["last_time"] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    # 4. write back to track.json
    track_json.append(new_entry)
    save_json_to_file(track_json, RESULT_PATH)
    return

def track(entry_id=ALL_ENTRIES):
    email_items = [] # list of tuple(entry, list of tuple(Item, status))
    # 1. read current track.json
    track_json = load_file_to_json(file_path=RESULT_PATH)
    if track_json == None:
        track_json = []
    new_track_json = []
    # 2. for each entry:
    for entry in track_json:
        if entry_id != ALL_ENTRIES and entry["id"] != entry_id:
            new_track_json.append(entry)
            continue
        email_entry_items = []
        # 2.1. update search result
        success, search_result = update(entry)
        if not success:
            logging.error(f"Update of {entry} failed, skipping")
            new_track_json.append(entry)
            continue
        # 2.2. compare with last result
        last_search_result_dict = entry["last_result"]
        search_result_dict = {}

        # site-specific actions
        if "site" not in entry or entry["site"] == SITE_MERCARI: # for backwards compatibility
            entry["site"] = SITE_MERCARI
            for item in search_result:
                search_result_dict[item.id] = {"price": item.price, "status": item.status}
                # 2.3. if anything new:
                if item.id not in last_search_result_dict: # New
                    email_entry_items.append((item, TRACK_STATUS_NEW))
                elif search_result_dict[item.id] != last_search_result_dict[item.id]: # Modified
                    modification = []
                    for key in search_result_dict[item.id]:
                        if key not in last_search_result_dict[item.id]:
                            modification.append("None" + "->" + prettify(key, search_result_dict[item.id][key]))
                        elif search_result_dict[item.id][key] != last_search_result_dict[item.id][key]:
                            modification.append(prettify(key, last_search_result_dict[item.id][key]) + "->" + prettify(key, search_result_dict[item.id][key]))
                        # print(key, modification)
                    email_entry_items.append((item, TRACK_STATUS_MODIFIED + "(" + ", ".join(modification) + ")"))
        elif entry["site"] == SITE_YAHOO_AUCTIONS:
            for item in search_result:
                search_result_dict[item[KEY_ITEM_ID]] = {KEY_CURRENT_PRICE: item[KEY_CURRENT_PRICE], KEY_BID_COUNT: item[KEY_BID_COUNT]}
                if item[KEY_ITEM_ID] not in last_search_result_dict: # New
                    email_entry_items.append((item, TRACK_STATUS_NEW))
                elif search_result_dict[item[KEY_ITEM_ID]] != last_search_result_dict[item[KEY_ITEM_ID]]: # Modified
                    modification = []
                    for key in search_result_dict[item[KEY_ITEM_ID]]:
                        if key not in last_search_result_dict[item[KEY_ITEM_ID]]:
                            modification.append("None" + "->" + prettify(key, search_result_dict[item[KEY_ITEM_ID]][key]))
                        elif search_result_dict[item[KEY_ITEM_ID]][key] != last_search_result_dict[item[KEY_ITEM_ID]][key]:
                            modification.append(prettify(key, last_search_result_dict[item[KEY_ITEM_ID]][key]) + "->" + prettify(key, search_result_dict[item[KEY_ITEM_ID]][key]))
                    email_entry_items.append((item, TRACK_STATUS_MODIFIED + "(" + ", ".join(modification) + ")"))

        entry["last_result"] = search_result_dict
        entry["last_time"] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        new_track_json.append(entry)
        if len(email_entry_items) > 0:
            email_items.append((entry, email_entry_items))
    # 2.4. send email
    if len(email_items) > 0:
        send_tracking_email(EmailConfig(email_config_path=EMAIL_CONFIG_PATH), email_items)
    else:
        print("nothing new")
    
    # 3. write back to track.json
    save_json_to_file(new_track_json, RESULT_PATH)
    return

def list_():
    track_json = load_file_to_json(file_path=RESULT_PATH)
    if track_json == None:
        track_json = []
    for entry in track_json:
        print(prettify("entry", entry))

if __name__ == "__main__":
    logging.basicConfig(filename="error.log", level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(description="Yambot")
    subparsers = parser.add_subparsers(dest='action')
    add_parser = subparsers.add_parser('add')
    list_parser = subparsers.add_parser('list')
    track_parser = subparsers.add_parser('track')
    track_parser.add_argument('--id', type=int, help='Specific entry id to track', default=None)
    args = parser.parse_args()
    try:
        if args.action == 'add':
            add()
        elif args.action == "list":
            list_()
        elif args.action == 'track':
            if args.id:
                track(entry_id=args.id)
            else:
                track()
    except Exception as e:
        logging.error(f"An error occurred:\n{e}", exc_info=True)
