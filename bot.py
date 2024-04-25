from json_utils import load_file_to_json, save_json_to_file
from mercari.mercari.mercari import search, MercariSort, MercariOrder, MercariSearchStatus, Item
from datetime import datetime
from email_utils import EmailConfig, send_tracking_email, prettify

CONFIG_PATH = "config.json"
RESULT_PATH = "track.json"

LEVEL_ABSOLUTE_UNIQUE = 1 # returns all results searched
LEVEL_UNIQUE = 2          # returns results with full keyword in their title
LEVEL_AMBIGUOUS = 3       # searches with supplemental keywords, returns results with full keyword in their title

CATEGORY_CD = 75

TRACK_STATUS_NEW = "New!!"
TRACK_STATUS_MODIFIED = "Modified"

def update(entry: dict) -> list[Item]:
    if entry["level"] == LEVEL_ABSOLUTE_UNIQUE or entry["level"] == LEVEL_UNIQUE:
        search_keyword = entry["keyword"]
    elif entry["level"] == LEVEL_AMBIGUOUS:
        search_keyword = entry["keyword"] + " " + entry["supplement"]
    else:
        raise ValueError("unknown level")

    search_result = list(search(search_keyword,
                               sort=MercariSort.SORT_SCORE,
                               order=MercariOrder.ORDER_DESC,
                               status=MercariSearchStatus.DEFAULT,
                               category_id=[entry["category_id"]]))

    if entry["level"] == LEVEL_ABSOLUTE_UNIQUE:
        filtered_search_result = search_result
    elif entry["level"] == LEVEL_UNIQUE or entry["level"] == LEVEL_AMBIGUOUS:
        filtered_search_result = []
        for item in search_result:
            if search_keyword in item.productName:
                filtered_search_result.append(item)
    
    return filtered_search_result    

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
    new_entry["id"] = max_entry_id + 1
    new_entry["keyword"] = input("search keyword: ")
    while True:
        level = int(input("keyword's ambiguity level: "))
        if level == LEVEL_ABSOLUTE_UNIQUE or level == LEVEL_UNIQUE:
            new_entry["level"] = level
            break
        elif level == LEVEL_AMBIGUOUS:
            new_entry["level"] = level
            new_entry["supplement"] = input("supplemental keyword: ")
            break
        else:
            print("level error")
            continue
    new_entry["category_id"] = int(input(f"category_id of search (None: 0, CD: {CATEGORY_CD}): "))
    
    # 3. initial update
    search_result = update(new_entry)
    search_result_dict = {}
    for item in search_result:
        search_result_dict[item.id] = {"price": item.price, "status": item.status}
    new_entry["last_result"] = search_result_dict
    new_entry["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 4. write back to track.json
    track_json.append(new_entry)
    save_json_to_file(track_json, RESULT_PATH)
    return

def track():
    # TODO
    email_items = [] # list of tuple(entry, list of tuple(Item, status))
    # 1. read current track.json
    track_json = load_file_to_json(file_path=RESULT_PATH)
    if track_json == None:
        track_json = []
    new_track_json = []    
    # 2. for each entry:
    for entry in track_json:
        email_entry_items = []
        # 2.1. update search result
        search_result = update(entry)
        # 2.2. compare with last result
        last_search_result_dict = entry["last_result"]
        search_result_dict = {}
        for item in search_result:
            search_result_dict[item.id] = {"price": item.price, "status": item.status}
            # 2.3. if anything new:
            if item.id not in last_search_result_dict: # New
                email_entry_items.append((item, TRACK_STATUS_NEW))
            elif search_result_dict[item.id] != last_search_result_dict[item.id]: # Modified
                modification = []
                for key in search_result_dict[item.id]:
                    if search_result_dict[item.id][key] != last_search_result_dict[item.id][key]:
                        modification.append(prettify(key, last_search_result_dict[item.id][key]) + "->" + prettify(key, search_result_dict[item.id][key]))
                    # print(key, modification)
                email_entry_items.append((item, TRACK_STATUS_MODIFIED + "(" + ", ".join(modification) + ")"))
        entry["last_result"] = search_result_dict
        entry["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_track_json.append(entry)
        if len(email_entry_items) > 0:
            stripped_entry = {key: value for key, value in entry.items() if key in ["id", "keyword", "level", "category_id", "supplement"]}
            email_items.append((stripped_entry, email_entry_items))
    # 2.4. send email
    if len(email_items) > 0:
        config_json = load_file_to_json(file_path=CONFIG_PATH)
        email_config = EmailConfig(config_json)
        send_tracking_email(email_config, email_items)
    else:
        print("nothing new")
    
    # 3. write back to track.json
    save_json_to_file(new_track_json, RESULT_PATH)
    return

if __name__ == "__main__":
    track()