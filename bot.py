from json_utils import load_file_to_json, save_json_to_file
from mercari.mercari.mercari import search, MercariSort, MercariOrder, MercariSearchStatus, Item
from datetime import datetime

CONFIG_PATH = "config.json"
RESULT_PATH = "track.json"

LEVEL_ABSOLUTE_UNIQUE = 1 # returns all results searched
LEVEL_UNIQUE = 2          # returns results with full keyword in their title
LEVEL_AMBIGUOUS = 3       # searches with supplemental keywords, returns results with full keyword in their title

CATEGORY_CD = 75

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
    # 1. read current track.json
    # 2. for each entry:
    # 2.1. update search result
    # 2.2. compare with last result
    # 2.3. if anything new: send email
    # 3. write back to track.json
    return

if __name__ == "__main__":
    add()