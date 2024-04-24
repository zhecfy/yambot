import smtplib
import requests

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.header import Header

import imghdr

from mercari.mercari.mercari import MercariItemStatus, Item

class EmailConfig:
    def __init__(self, config_json):
        self.MAIL_HOST = config_json["MAIL_HOST"]
        self.MAIL_SENDER = config_json["MAIL_SENDER"]
        self.MAIL_LICENSE = config_json["MAIL_LICENSE"]
        self.MAIL_RECEIVER = config_json["MAIL_RECEIVER"]
        self.MAIL_RECEIVERS = [self.MAIL_RECEIVER]

def prettify(status):
    if status == MercariItemStatus.ITEM_STATUS_ON_SALE:
        return 'On Sale'
    elif status == MercariItemStatus.ITEM_STATUS_SOLD_OUT:
        return 'Sold Out'
    elif status == MercariItemStatus.ITEM_STATUS_TRADING:
        return 'Trading'
    else:
        return status

def send_email (config: EmailConfig, searchKeyword: str, searchResult: list[Item]):
    mail_message = MIMEMultipart()
    mail_message["Subject"] = Header(f"Mercari search result for {searchKeyword}", "utf-8")
    mail_message["From"] = f"Mercari bot<{config.MAIL_SENDER}>"
    mail_message["To"] = f"{config.MAIL_RECEIVER}"

    html = f"""<p>Mercari search result for {searchKeyword}:</p>"""

    for item in searchResult:
        html += f"""
        <p><a href="{item.productURL}">{item.productName}</a> (￥{item.price}, {prettify(item.status)})</p>
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
        smtp.login(config.MAIL_SENDER, config.MAIL_LICENSE)
        smtp.sendmail(config.MAIL_SENDER, config.MAIL_RECEIVERS, mail_message.as_string())
        smtp.quit()
        print("send success")