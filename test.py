from mercari.mercari.mercari import search, MercariSearchStatus, MercariSort, MercariOrder, MercariItemStatus
from json_utils import save_json_to_file, load_file_to_json

CATEGORY_CD = 75
CONFIG_PATH = "config.json"

searchKeyword = input("search keyword: ")
# searchKeyword = "Palace Memories"

searchResult = list(search(searchKeyword,
                           sort=MercariSort.SORT_SCORE,
                           order=MercariOrder.ORDER_DESC,
                           status=MercariSearchStatus.DEFAULT,
                           category_id=[CATEGORY_CD]))

filtered_searchResult = []
for item in searchResult:
    if searchKeyword in item.productName:
        filtered_searchResult.append(item)
searchResult = filtered_searchResult

for item in searchResult:
    print()
    print("{}\n{}\n{}\n{}\n{}".format(item.productName, item.productURL, item.imageURL, item.price, item.status))

##### email

ch = input("Send email? (y/n):")
if (ch == 'y'):
    from email_utils import EmailConfig, send_email
    config_json = load_file_to_json(file_path=CONFIG_PATH)
    email_config = EmailConfig(config_json)
    send_email(email_config, searchKeyword, searchResult)
