import requests
import smtplib
import imghdr
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Dict, Tuple
from mercari.mercari.mercari import MercariItemStatus, Item
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

def prettify(type: str, value) -> str:
    # print("in prettify", type, value)
    if type == "status":
        if value == MercariItemStatus.ITEM_STATUS_ON_SALE:
            return 'On Sale'
        elif value == MercariItemStatus.ITEM_STATUS_SOLD_OUT:
            return 'Sold Out'
        elif value == MercariItemStatus.ITEM_STATUS_TRADING:
            return 'Trading'
        else:
            return value
    elif type == "price":
        return "￥" + str(value)
    elif type == "entry":
        if value["level"] == LEVEL_ABSOLUTE_UNIQUE or value["level"] == LEVEL_UNIQUE:
            return f"\"{value["keyword"]}\" (id: {value["id"]}, Level: {value["level"]}, Category: {prettify("category_id", value["category_id"])})"
        elif value["level"] == LEVEL_AMBIGUOUS:
            return f"\"{value["keyword"]}\"+\"{value["supplement"]}\" (id: {value["id"]}, Level: {value["level"]}, Category: {prettify("category_id", value["category_id"])})"
        else:
            return str(value)
    elif type == "category_id":
        if value == 0:
            return "all"
        elif value == CATEGORY_CD:
            return "CD"
        else:
            return str(value)        
    else:
        return str(value)

def send_email (config: EmailConfig, searchKeyword: str, searchResult: List[Item]):
    mail_message = MIMEMultipart()
    mail_message["Subject"] = Header(f"Mercari search result for {searchKeyword}", "utf-8")
    mail_message["From"] = f"Mercari bot<{config.MAIL_SENDER}>"
    mail_message["To"] = f"{config.MAIL_RECEIVER}"

    html = f"""<p>Mercari search result for {searchKeyword}:</p>"""

    for item in searchResult:
        html += f"""
        <p><a href="{item.productURL}">{item.productName}</a> ({prettify("price", item.price)}, {prettify("status", item.status)})</p>
        <p><img src="cid:{item.id}"></p>"""

    html = "<html><body>" + html + "</body></html>"
    # print(html)
    mail_message.attach(MIMEText(html, 'html'))

    for item in searchResult:
        image_resp = requests.get(item.imageURL).content
        image_type = imghdr.what(None, image_resp)
        # print(image_type)
        image = MIMEImage(image_resp, image_type)
        image.add_header('Content-Disposition', 'inline', filename=('utf-8', 'ja', item.productName + '.' + image_type))
        image.add_header("Content-ID", f"<{item.id}>")
        mail_message.attach(image)
    # print(mail_message)

    with smtplib.SMTP_SSL(config.MAIL_HOST, 465) as smtp:
        # smtp.set_debuglevel(1)
        smtp.login(config.MAIL_SENDER, config.MAIL_PASSWORD)
        smtp.sendmail(config.MAIL_SENDER, config.MAIL_RECEIVERS, mail_message.as_string())
        smtp.quit()
        print("send success")

def send_tracking_email (config: EmailConfig, email_items: List[Tuple[Dict, List[Tuple[Item, str]]]]):
    # email_items: list of tuple(entry, list of tuple(Item, status))
    mail_message = MIMEMultipart()

    title_keywords = []
    for (entry, email_entry_items) in email_items:
        title_keywords.append(entry["keyword"])
    mail_message["Subject"] = Header(f"Tracking update for {", ".join(title_keywords)}", "utf-8")
    mail_message["From"] = f"Mercari bot<{config.MAIL_SENDER}>"
    mail_message["To"] = f"{config.MAIL_RECEIVER}"

    html = ""
    images = []

    for (entry, email_entry_items) in email_items:
        entry_html = f"<h2>Tracking update for {prettify("entry", entry)}</h2>\n"
        for (item, status) in email_entry_items:
            # html
            entry_html += f"""<p>[{status}]<a href="{item.productURL}">{item.productName}</a> ({prettify("price", item.price)}, {prettify("status", item.status)})</p>
            <p><img src="cid:{item.id}"></p>\n"""

            # image
            image_resp = requests.get(item.imageURL).content
            image_type = imghdr.what(None, image_resp)
            image = MIMEImage(image_resp, image_type)
            image.add_header('Content-Disposition', 'inline', filename=('utf-8', 'ja', item.productName + '.' + image_type))
            image.add_header("Content-ID", f"<{item.id}>")
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