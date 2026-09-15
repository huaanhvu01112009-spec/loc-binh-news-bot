import os
import json
import requests
import feedparser
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Không tìm thấy TELEGRAM_BOT_TOKEN")

API = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = "subscribers.json"
UPDATE_FILE = "last_update_id.txt"

VN = timezone(timedelta(hours=7))

RSS_URLS = [
    "https://news.google.com/rss/search?q=Lộc+Bình+Lạng+Sơn&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=Lộc+Bình&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=Chi+Ma+Lạng+Sơn&hl=vi&gl=VN&ceid=VN:vi",
]


def telegram(method, data=None):
    response = requests.post(
        f"{API}/{method}",
        data=data or {},
        timeout=30
    )
    return response.json()


def load_subscribers():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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
    except Exception:
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
                "text": (
                    f"📰 BẢN TIN LỘC BÌNH\n"
                    f"📅 {today}\n\n"
                    "Chưa tìm thấy tin mới."
                )
            }
        )
        return

    text = (
        f"📰 <b>BẢN TIN LỘC BÌNH</b>\n"
        f"📅 {today}\n\n"
    )

    for i, article in enumerate(articles[:7], 1):
        text += (
            f"{i}. <b>{article['title']}</b>\n"
            f"🔗 {article['link']}\n\n"
        )

    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true"
        }
    )


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return

    text = message.get("text", "").strip()

    subscribers = load_subscribers()

    if text.startswith("/start"):

        if chat_id not in subscribers:
            subscribers.append(chat_id)
            save_subscribers(subscribers)

        telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": (
                    "👋 <b>Xin chào!</b>\n\n"
                    "🤖 <b>LỘC BÌNH NEWS BOT</b>\n\n"
                    "Bot cập nhật tin tức Lộc Bình – Lạng Sơn.\n\n"
                    "📰 /news - Tin mới nhất\n"
                    "🔔 /subscribe - Nhận bản tin mỗi ngày\n"
                    "🔕 /unsubscribe - Tắt bản tin\n"
                    "ℹ️ /help - Trợ giúp"
                ),
                "parse_mode": "HTML"
            }
        )

    elif text.startswith("/news"):
        send_news(chat_id)

    elif text.startswith("/today"):
        send_news(chat_id)

    elif text.startswith("/subscribe"):

        if chat_id not in subscribers:
            subscribers.append(chat_id)
            save_subscribers(subscribers)

        telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "🔔 Đã bật nhận bản tin mỗi ngày!"
            }
        )

    elif text.startswith("/unsubscribe"):

        if chat_id in subscribers:
            subscribers.remove(chat_id)
            save_subscribers(subscribers)

        telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "🔕 Đã tắt nhận bản tin."
            }
        )

    elif text.startswith("/help"):

        telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": (
                    "ℹ️ <b>HƯỚNG DẪN</b>\n\n"
                    "/start - Bắt đầu\n"
                    "/news - Tin mới nhất\n"
                    "/today - Bản tin hôm nay\n"
                    "/subscribe - Nhận tin mỗi ngày\n"
                    "/unsubscribe - Tắt tin"
                ),
                "parse_mode": "HTML"
            }
        )


def check_updates():
    last_update = get_last_update()

    result = telegram(
        "getUpdates",
        {
            "offset": last_update + 1,
            "timeout": 5,
            "allowed_updates": json.dumps(["message"])
        }
    )

    if not result.get("ok"):
        print("Telegram ERROR:", result)
        return

    updates = result.get("result", [])

    newest = last_update

    for update in updates:

        update_id = update.get("update_id", 0)

        if update_id > newest:
            newest = update_id

        message = update.get("message")

        if message:
            handle_message(message)

    if newest != last_update:
        save_last_update(newest)


def main():
    print("🤖 Lộc Bình News Bot đang chạy...")

    me = telegram("getMe")

    if me.get("ok"):
        username = me["result"].get("username")
        print(f"✅ Telegram kết nối thành công: @{username}")
    else:
        print("❌ Không thể kết nối Telegram")
        print(me)
        return

    check_updates()

    print("✅ Bot đã hoàn thành lần kiểm tra.")


if __name__ == "__main__":
    main()
