import pandas as pd
import csv
import sqlite3
import urllib3
import smtplib
import requests
from datetime import datetime
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

DATABASE = "boletin_summary.db"
CSV_FILE = "boletin_summary.csv"
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
        print("Email sent successfully")
    except smtplib.SMTPException as e:
        print(f"Error sending email: {e}")

def database():
    try:
        connection = sqlite3.connect(DATABASE)
        return connection
    except sqlite3.Error as e:
        print(f"Database error: {e}")
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
        print(f"Database error: {e}")

def delete_item():
    conn = database()
    statement = "delete from sha256 where value='80f142a157ee0e9c36d61cf6ce91026fe8608695c317b1ddd1103ef04fa51b57'"
    cursor = conn.cursor()
    cursor.execute(statement)
    conn.commit()
    conn.close()

def get_feed_data(feed_url):
    try:
        response = requests.get(feed_url, verify=False)
        response.raise_for_status()
        response = response.text.strip().splitlines()
        clean_response = [line for line in response if line]
        return clean_response
    except requests.exceptions.RequestException as e:
        print(f"Error fetching feed data: {e}")
        return None

def check_value_in_db(feed_type, values):
    conn = database()
    cursor = conn.cursor()

    for value in values:
        cursor.execute(f"SELECT value FROM {feed_type} WHERE value = ?", (value,))
        if cursor.fetchone():
            return False
    conn.close()

    return values

def add_data_to_db(feed_type, new_elements):
    if not new_elements:
        return {"status": "error", "message": "No new elements to add to the database."}

    date = datetime.now().strftime("%Y-%m-%d")
    conn = database()
    cursor = conn.cursor()
    cursor.executemany(f"INSERT INTO {feed_type} (value, date) VALUES (?,?)", [(element, date) for element in new_elements])
    conn.commit()
    conn.close()

def csv_exporter(new_data):
    if not new_data:
        print("No hay elementos nuevos para exportar.")
        return None

    filename = "boletin_summary.xlsx"
    with pd.ExcelWriter(filename) as writer:
        for feed_type in new_data.keys():
            df = pd.DataFrame(new_data[feed_type], columns=["value"])
            df.to_excel(writer, sheet_name=feed_type, index=False)

    return filename

def main():
    all_new_data = {}

    for feed_type, feed_url in FEEDS.items():
        feed_data = get_feed_data(feed_url)

        if feed_data:
            new_elements = check_value_in_db(feed_type, feed_data)

            if new_elements:
                all_new_data[feed_type] = new_elements
                add_data_to_db(feed_type, new_elements)

    csv_file = csv_exporter(all_new_data)

    if csv_file:
        send_email(subject="----- Boletin summary -----", body="Actualización de contenido boletín", attachment=csv_file)
    else:
        print("No se detectaron nuevos elementos. No se enviará correo.")

if __name__ == "__main__":
    # setup_database()
    # delete_item()
    main()