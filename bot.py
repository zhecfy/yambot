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

def update(entry: dict) -> Tuple[bool, List]:
    if "site" not in entry or entry["site"] == SITE_MERCARI: # for backwards compatibility
        if entry["level"] == LEVEL_ABSOLUTELY_UNIQUE or entry["level"] == LEVEL_UNIQUE:
            search_keyword = entry["keyword"]
        elif entry["level"] == LEVEL_AMBIGUOUS:
            search_keyword = entry["keyword"] + " " + entry["supplement"]
        else:
            raise ValueError("unknown level")

        category_id = entry["category_id"]
        if isinstance(entry["category_id"], int): # backwards compatibility
            category_id = [entry["category_id"]]

        item_condition_id = []
        if "item_condition_id" in entry:
            item_condition_id = entry["item_condition_id"]

        success, search_result = search_mercari(search_keyword,
                                                sort=MercariSort.SORT_SCORE,
                                                order=MercariOrder.ORDER_DESC,
                                                status=MercariSearchStatus.DEFAULT,
                                                category_id=category_id,
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

        if "auccat" in parameters and parameters["auccat"] == 0:
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

    # keyword (mercari) or p (yahoo_auctions)
    if new_entry["site"] == SITE_MERCARI:
        new_entry["keyword"] = input("search keyword: ")
    elif new_entry["site"] == SITE_YAHOO_AUCTIONS:
        new_entry["p"] = input("search keyword: ")

    # level (mercari only)
    if new_entry["site"] == SITE_MERCARI:
        while True:
            level = int(input("""**********
Yambot's Ambiguity Levels for Mercari
                              
- Level 1 (Absolutely Unique): track all items
- Level 2 (Unique): track items with full keyword in their title
- Level 3 (Ambiguous): search with supplemental keywords, track items with full keyword in their title
**********
keyword's ambiguity level: """))
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
    
    # category_id (mercari) or auccat (yahoo_auctions)
    if new_entry["site"] == SITE_MERCARI:
        new_entry["category_id"] = int(input(f"category_id of search (all: 0, CD: {MERCARI_CATEGORY_CD}): "))
    elif new_entry["site"] == SITE_YAHOO_AUCTIONS:
        new_entry["auccat"] = int(input(f"auccat of search (all: 0, Music: {YAHOO_CATEGORY_MUSIC}): "))
    
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
