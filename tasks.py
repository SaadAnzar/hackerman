import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from celery import Celery
from celery.schedules import crontab

load_dotenv()

app = Celery("tasks", broker=os.getenv("CELERY_BROKER_URL"))

app.conf.beat_schedule = {
    "scrape-and-email-every-day": {
        "task": "tasks.scrape_and_email",
        "schedule": crontab(hour=0, minute=0),
    },
}

app.conf.timezone = "Asia/Kolkata"


@app.task
def scrape_and_email():

    def scrape_website():
        try:
            page = requests.get("https://news.ycombinator.com/newest")
            page.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching the page: {e}")
            return []

        soup = BeautifulSoup(page.content, "html.parser")

        articles_list = []

        articles = soup.find_all("span", class_="titleline")

        for article in articles:
            article_link = article.find("a")
            article_link_text = article_link.get_text()
            article_link_href = article_link["href"]

            articles_list.append(
                {"title": article_link_text, "link": article_link_href}
            )

        print("Scraped articles successfully!")

        return articles_list

    def send_email(to_email, subject, message):
        from_email = os.getenv("EMAIL_USERNAME")
        password = os.getenv("EMAIL_PASSWORD")

        if not from_email or not password:
            raise ValueError("Email username or password not provided.")

        msg = MIMEMultipart()
        msg["From"] = f"HackerMan <{from_email}>"
        msg["To"] = ", ".join(to_email)
        msg["Subject"] = subject

        msg.attach(MIMEText(message, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.ehlo()
            server.login(from_email, password)
            server.send_message(msg)
            server.quit()
            print("Email sent successfully!")

        except smtplib.SMTPAuthenticationError as e:
            print("Failed to authenticate with the SMTP server.\n", e)

    articles = scrape_website()

    articles_html = "<ul>"
    for article in articles:
        articles_html += f'<li><a href="{article["link"]}">{article["title"]}</a></li>'
    articles_html += "</ul>"

    recipients = [
        "anzarhps@gmail.com",
        "direghost001@gmail.com",
    ]

    send_email(recipients, "Latest Hacker News Articles", articles_html)
