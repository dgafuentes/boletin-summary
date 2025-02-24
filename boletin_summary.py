import time
import pandas as pd
import sqlite3
import urllib3
import smtplib
import requests
import logging
from datetime import datetime
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from requests.packages.urllib3.exceptions import InsecureRequestWarning

DATABASE = "boletin_summary.db"
FILENAME = "boletin-summary.xlsx"

logging.basicConfig(filename="boletin-summary.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(funcName)s: %(message)s", datefmt="%d-%m-%y %H:%M")

FEEDS = {
    "domain": "https://tip.develsecurity.com/feeds/2cdf4671-c9b0-476a-ac99-b7fedb7191c4",
    "md5": "https://tip.develsecurity.com/feeds/e9dded32-1fa0-4e93-b6be-aba781160cca",
    "sha1": "https://tip.develsecurity.com/feeds/4ef4cb7f-266a-4f80-b867-bbc0e8bcf34c",
    "sha256": "https://tip.develsecurity.com/feeds/a0076371-7558-4fed-bbcd-033710ca7601",
    "url": "https://tip.develsecurity.com/feeds/02883260-7048-4e5e-811e-fa1d0040cbbf",
    "ip": "https://tip.develsecurity.com/feeds/54228bec-a841-4ff8-b68e-091aa35dd9dc"
}

EMAIL_CONFIG = {
    "destination": "xxx@gmail.com",
    "smtp_server": "email-smtp:587",
    "username": "username",
    "password": "password",
    "email_from": "boletin-summary@mail.com",
    "ssl_enable": False
}

def send_email(subject, body, attachment=None):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_CONFIG["email_from"]
    msg["To"] = EMAIL_CONFIG["destination"]
    msg["Subject"] = subject
    email_smtp_server = EMAIL_CONFIG["smtp_server"]
    msg.attach(MIMEText(body, "plain"))

    if attachment:
        with open(attachment, "rb") as attachment_file:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment_file.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {attachment}",
            )
            msg.attach(part)

    try:
        if EMAIL_CONFIG["ssl_enable"]:
            server = smtplib.SMTP_SSL(email_smtp_server)
        else:
            server = smtplib.SMTP(email_smtp_server)
            server.starttls()

        server.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
        server.sendmail(EMAIL_CONFIG["email_from"], EMAIL_CONFIG["destination"], msg.as_string())
        server.quit()
        logging.info("Email sent successfully")
    except smtplib.SMTPException as e:
        logging.error(f"Error sending email: {e}")

def database():
    try:
        connection = sqlite3.connect(DATABASE)
        return connection
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None

def setup_database():
    try:
        conn = database()
        cursor = conn.cursor()

        for feed_type in FEEDS.keys():
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {feed_type} (value TEXT PRIMARY KEY, date TEXT)")
        
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

def delete_items():
    conn = database()
    indicators = {
        "domain": ["arc4.new", "aazsbsgya565vlu2c6bzy6yfiebkcbtvvcytvolt33s77xypi7nypxyd.onion", "n2.skype"],
        "md5": ["6ed4f5f04d62b18d96b26d6db7c18840", "7688c1b7a1124c1cd9413f4b535b2f44"],
        "sha1": ["c7a37c0edeffd23777cca44f9b49076be1bd43e6", "f048e5651a28ff302d257d0c92063f3f90d08988"],
        "sha256": ["17205c43189c22dfcb278f5cc45c2562f622b0b6280dcd43cc1d3c274095eb90"],
        "ip": ["87.249.138.47", "45.55.158.47", "5.8.63.178"],
        "url": ["https://ssnagov-report.vipcase.bg/?s=2734430", "https://smbeckwithlaw.com/1.zip", "https://ongish.net/1stnb/", "https://heilee.com/qxz3l"]
    }

    cursor = conn.cursor()
    for feed_type, values in indicators.items():
        [print(f"-> Indicator={indicator}") for indicator in values]
        for indicator in values:
            statement = f"delete from {feed_type} where value='{indicator}'"
            cursor.execute(statement)
            conn.commit()
    conn.close()

def get_feed_data(feed_url, max_retries=10, delay=5):
    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(feed_url, verify=False, timeout=10)
            response.raise_for_status()
            response = response.text.strip().splitlines()
            clean_response = [line for line in response if line]
            return clean_response
        except requests.exceptions.RequestException as error:
            logging.error(f"Error fetching feed data: {error} - Attempt {attempt + 1}/{max_retries} trying to connect to {feed_url}")
            attempt += 1
            time.sleep(delay)

def check_value_in_db(feed_type, values):
    new_indicators = []
    conn = database()
    cursor = conn.cursor()

    for value in values:
        statement = f"SELECT value FROM {feed_type} WHERE value = ?"
        cursor.execute(statement, (value,))
        data = cursor.fetchone()

        if not data:
            logging.info(f"New indicator found: {value}")
            new_indicators.append(value)

    conn.close()

    return new_indicators

def add_data_to_db(feed_type, new_elements):
    if not new_elements:
        logging.info("No new elements to add to the database.")
        return None

    date = datetime.now().strftime("%Y-%m-%d")
    conn = database()
    cursor = conn.cursor()
    cursor.executemany(f"INSERT INTO {feed_type} (value, date) VALUES (?,?)", [(element, date) for element in new_elements])
    conn.commit()
    conn.close()

def file_exporter(new_data):
    if not new_data:
        logging.info("No hay elementos nuevos para exportar.")
        return None

    with pd.ExcelWriter(FILENAME) as writer:
        for feed_type in new_data.keys():
            df = pd.DataFrame(new_data[feed_type], columns=["Indicator"])
            df.to_excel(writer, sheet_name=feed_type, index=False)

    return FILENAME

def main():
    all_new_data = {}

    for feed_type, feed_url in FEEDS.items():
        feed_data = get_feed_data(feed_url)

        if feed_data:
            new_elements = check_value_in_db(feed_type, feed_data)

            if new_elements:
                all_new_data[feed_type] = new_elements
                add_data_to_db(feed_type, new_elements)

    boletin_file = file_exporter(all_new_data)

    if boletin_file:
        send_email(subject="----- Boletin summary -----", body="Actualización de contenido boletín", attachment=boletin_file)
    else:
        logging.info("No se envía correo.")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    setup_database()
    main()
