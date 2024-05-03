import requests
import smtplib
import imghdr
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Dict, Tuple

from mercari.mercari.mercari import MercariItemStatus, Item

from Yoku.yoku.consts import KEY_TITLE, KEY_IMAGE, KEY_URL, KEY_POST_TIMESTAMP, KEY_END_TIMESTAMP, KEY_START_TIMESTAMP, KEY_ITEM_ID, KEY_BUYNOW_PRICE, KEY_CURRENT_PRICE, KEY_START_PRICE, KEY_BID_COUNT
from Yoku.yoku.scrape import prettify_timestamp

from config import *
from json_utils import load_file_to_json

class EmailConfig:
    def __init__(self, email_config_path):
        config_json = load_file_to_json(file_path=email_config_path)
        self.MAIL_HOST = config_json["MAIL_HOST"]
        self.MAIL_SENDER = config_json["MAIL_SENDER"]
        self.MAIL_PASSWORD = config_json["MAIL_PASSWORD"]
        self.MAIL_RECEIVER = config_json["MAIL_RECEIVER"]
        self.MAIL_RECEIVERS = [self.MAIL_RECEIVER]

def prettify(type_: str, value) -> str:
    # print("in prettify", type_, value)
    if type_ == "status":
        if value == MercariItemStatus.ITEM_STATUS_ON_SALE:
            return 'On Sale'
        elif value == MercariItemStatus.ITEM_STATUS_SOLD_OUT:
            return 'Sold Out'
        elif value == MercariItemStatus.ITEM_STATUS_TRADING:
            return 'Trading'
        else:
            return value
    elif type_ == "price" or type_ == KEY_CURRENT_PRICE:
        return "￥" + str(value)
    elif type_ == "entry":
        if "site" not in value or value["site"] == SITE_MERCARI:
            if value["level"] == LEVEL_ABSOLUTELY_UNIQUE or value["level"] == LEVEL_UNIQUE:
                return f"\"{value["keyword"]}\" (id: {value["id"]}, Mercari, Level: {value["level"]}, Category: {prettify("category_id", value["category_id"])})"
            elif value["level"] == LEVEL_AMBIGUOUS:
                return f"\"{value["keyword"]}\"+\"{value["supplement"]}\" (id: {value["id"]}, Mercari, Level: {value["level"]}, Category: {prettify("category_id", value["category_id"])})"
        elif value["site"] == SITE_YAHOO_AUCTIONS:
            return f"\"{value["p"]}\" (id: {value["id"]}, Yahoo! Auctions, Category: {prettify("auccat", value["auccat"])})"
        else:
            return str(value)
    elif type_ == "category_id":
        if value == 0:
            return "all"
        elif value == MERCARI_CATEGORY_CD:
            return "CD"
        else:
            return str(value)
    elif type_ == "auccat":
        if value == 0:
            return "all"
        elif value == YAHOO_CATEGORY_MUSIC:
            return "Music"
        else:
            return str(value)
    elif type_ == KEY_END_TIMESTAMP:
        if type(value) == int:
            return prettify_timestamp(value)
        else:
            return str(value)
    elif type_ == KEY_BID_COUNT:
        if value == 0 or value == 1:
            return f"{value} bid"
        else:
            return f"{value} bids"
    else:
        return str(value)

def send_tracking_email (config: EmailConfig, email_items: List[Tuple[Dict, List[Tuple[Item, str]]]]):
    # email_items: list of tuple(entry, list of tuple(Item, status))
    mail_message = MIMEMultipart()

    title_keywords = []
    for (entry, email_entry_items) in email_items:
        title_keywords.append(entry["keyword"] if "keyword" in entry else entry["p"])
    mail_message["Subject"] = Header(f"Tracking update for {", ".join(title_keywords)}", "utf-8")
    mail_message["From"] = f"Yambot<{config.MAIL_SENDER}>"
    mail_message["To"] = f"{config.MAIL_RECEIVER}"

    html = ""
    images = []

    for (entry, email_entry_items) in email_items:
        entry_html = f"<h2>Tracking update for {prettify("entry", entry)}</h2>\n"
        for (item, status) in email_entry_items:
            # html
            if "site" not in entry or entry["site"] == SITE_MERCARI:
                entry_html += f"""<p>[{status}]<a href="{item.productURL}">{item.productName}</a> ({prettify("price", item.price)}, {prettify("status", item.status)})</p>
                <p><img src="cid:{item.id}"></p>\n"""
            elif entry["site"] == SITE_YAHOO_AUCTIONS:
                entry_html += f"""<p>[{status}]<a href="{item[KEY_URL]}">{item[KEY_TITLE]}</a> ({prettify(KEY_CURRENT_PRICE, item[KEY_CURRENT_PRICE])}, {prettify(KEY_BID_COUNT, item[KEY_BID_COUNT])})</p>
                <p><img src="cid:{item[KEY_ITEM_ID]}"></p>\n"""

            # image
            if "site" not in entry or entry["site"] == SITE_MERCARI:
                image_resp = requests.get(item.imageURL).content
            elif entry["site"] == SITE_YAHOO_AUCTIONS:
                image_resp = requests.get(item[KEY_IMAGE]).content
            
            image_type = imghdr.what(None, image_resp)
            image = MIMEImage(image_resp, image_type)
            
            if "site" not in entry or entry["site"] == SITE_MERCARI:
                image.add_header('Content-Disposition', 'inline', filename=('utf-8', 'ja', item.productName + '.' + image_type))
                image.add_header("Content-ID", f"<{item.id}>")
            elif entry["site"] == SITE_YAHOO_AUCTIONS:
                image.add_header('Content-Disposition', 'inline', filename=('utf-8', 'ja', item[KEY_TITLE] + '.' + image_type))
                image.add_header("Content-ID", f"<{item[KEY_ITEM_ID]}>")
            
            images.append(image)
        html += entry_html
    
    html = "<html><body>" + html + "</body></html>"
    mail_message.attach(MIMEText(html, 'html'))
    for image in images:
        mail_message.attach(image)
    
    with smtplib.SMTP_SSL(config.MAIL_HOST, 465) as smtp:
        # smtp.set_debuglevel(1)
        smtp.login(config.MAIL_SENDER, config.MAIL_PASSWORD)
        smtp.sendmail(config.MAIL_SENDER, config.MAIL_RECEIVERS, mail_message.as_string())
        smtp.quit()
        print("send success")