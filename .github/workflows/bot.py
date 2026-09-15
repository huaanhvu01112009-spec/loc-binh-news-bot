
import os
import json
import time
import requests
import feedparser
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Không tìm thấy TELEGRAM_BOT_TOKEN")

API = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "subscribers.json"
UPDATE_FILE = "last_update_id.txt"

RSS_URLS = [
    "https://news.google.com/rss/search?q=Lộc+Bình+Lạng+Sơn&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=Lộc+Bình&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=Chi+Ma+Lạng+Sơn&hl=vi&gl=VN&ceid=VN:vi",
]

VN = timezone(timedelta(hours=7))


def telegram(method, data=None):
    r = requests.post(
        f"{API}/{method}",
        data=data or {},
        timeout=30
    )
    return r.json()


def load_subscribers():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_subscribers(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_last_update():
    if not os.path.exists(UPDATE_FILE):
        return 0

    try:
        with open(UPDATE_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0


def save_last_update(update_id):
    with open(UPDATE_FILE, "w") as f:
        f.write(str(update_id))


def get_news():
    articles = []

    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)

            for item in feed.entries[:10]:
                title = item.get("title", "").strip()
                link = item.get("link", "").strip()

                if not title or not link:
                    continue

                articles.append({
                    "title": title,
                    "link": link
                })

        except Exception as e:
            print("RSS ERROR:", e)

    unique = {}
    for article in articles:
        unique[article["link"]] = article

    return list(unique.values())[:10]


def send_news(chat_id):
    articles = get_news()

    today = datetime.now(VN).strftime("%d/%m/%Y")

    if not articles:
        telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": f"📰 BẢN TIN LỘC BÌNH\n📅 {today}\n\nChưa tìm thấy tin mới."
            }
        )
        return

    text = f"📰 <b>BẢN TIN LỘC BÌNH</b>\n📅 {today}\n\n"

    for i, article in enumerate(articles[:7], 1):
        text += (
            f"{i}. <b>{article['title']}</b>\n"
            f"🔗 {article['link']}\
