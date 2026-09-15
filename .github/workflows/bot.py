import os
import json
import re
import time
import hashlib
from datetime import datetime, timezone, timedelta

import requests
import feedparser
from telegram import Bot


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Chưa có TELEGRAM_BOT_TOKEN")


# =========================
# CẤU HÌNH
# =========================

VN_TZ = timezone(timedelta(hours=7))

DATA_FILE = "subscribers.json"
UPDATE_FILE = "last_update_id.txt"

RSS_URLS = [
    "https://news.google.com/rss/search?q=Lộc+Bình+Lạng+Sơn&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=Lộc+Bình&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=Chi+Ma+Lạng+Sơn&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=Na+Dương+Lạng+Sơn&hl=vi&gl=VN&ceid=VN:vi",
]

KEYWORDS = [
    "lộc bình",
    "chi ma",
    "na dương",
    "na duong",
    "mẫu sơn",
    "mau son",
    "lạng sơn",
    "lang son",
]

IMPORTANT_KEYWORDS = [
    "khẩn",
    "cảnh báo",
    "tai nạn",
    "giao thông",
    "cháy",
    "mưa",
    "bão",
    "lũ",
    "cửa khẩu",
    "chi ma",
    "lộc bình",
]


# =========================
# FILE DATA
# =========================

def load_subscribers():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_subscribers(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_last_update_id():
    if not os.path.exists(UPDATE_FILE):
        return 0

    try:
        with open(UPDATE_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0


def save_last_update_id(update_id):
    with open(UPDATE_FILE, "w") as f:
        f.write(str(update_id))


# =========================
# LẤY TIN
# =========================

def clean_html(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    return text.strip()


def article_id(title, link):
    raw = title + link
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_news():
    articles = []

    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)

            for item in feed.entries[:15]:
                title = clean_html(item.get("title", ""))
                link = item.get("link", "")
                summary = clean_html(item.get("summary", ""))

                text = (title + " " + summary).lower()

                if not any(keyword in text for keyword in KEYWORDS):
                    continue

                articles.append({
                    "id": article_id(title, link),
                    "title": title,
                    "summary": summary[:500],
                    "link": link,
                    "important": any(k in text for k in IMPORTANT_KEYWORDS)
                })

        except Exception as e:
            print("RSS error:", e)

    # loại trùng
    unique = {}
    for article in articles:
        unique[article["id"]] = article

    articles = list(unique.values())

    # Tin quan trọng lên đầu
    articles.sort(
        key=lambda x: x["important"],
        reverse=True
    )

    return articles[:10]


# =========================
# FORMAT TIN
# =========================

def format_article(article, number=None):

    prefix = f"{number}️⃣ " if number else ""

    text = f"{prefix}📰 <b>{article['title']}</b>\n\n"

    if article["summary"]:
        summary = article["summary"]

        if len(summary) > 350:
            summary = summary[:350] + "..."

        text += f"📝 {summary}\n\n"

    text += f"🔗 <a href=\"{article['link']}\">Đọc bài gốc</a>"

    return text


def make_daily_news():

    articles = get_news()

    today = datetime.now(VN_TZ).strftime("%d/%m/%Y")

    if not articles:
        return (
            f"🌅 <b>BẢN TIN LỘC BÌNH</b>\n"
            f"📅 {today}\n\n"
            f"Hiện chưa tìm thấy tin mới phù hợp.\n\n"
            f"🤖 Lộc Bình News Bot"
        )

    text = (
        f"🌅 <b>BẢN TIN LỘC BÌNH</b>\n"
        f"📅 {today}\n\n"
        f"🔥 <b>{len(articles)} tin đáng chú ý</b>\n\n"
    )

    for i, article in enumerate(articles[:7], 1):
        text += format_article(article, i)
        text += "\n\n━━━━━━━━━━━━━━\n\n"

    text += "📍 Lộc Bình – Lạng Sơn\n"
    text += "🤖 Lộc Bình News Bot"

    return text


# =========================
# XỬ LÝ LỆNH TELEGRAM
# =========================

def handle_message(bot, message):

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return

    text = message.get("text", "").strip()

    subscribers = load_subscribers()

    # START
    if text.startswith("/start"):

        if chat_id not in subscribers:
            subscribers.append(chat_id)
            save_subscribers(subscribers)

        bot.send_message(
            chat_id=chat_id,
            text=(
                "👋 <b>Xin chào!</b>\n\n"
                "🤖 <b>LỘC BÌNH NEWS BOT</b>\n\n"
                "Bot giúp bạn cập nhật những tin "
                "mới liên quan đến Lộc Bình – Lạng Sơn.\n\n"
                "📰 /news — Tin mới nhất\n"
                "📅 /today — Bản tin hôm nay\n"
                "🔔 /subscribe — Nhận bản tin mỗi ngày\n"
                "🔕 /unsubscribe — Tắt bản tin\n"
                "ℹ️ /help — Hướng dẫn"
            ),
            parse_mode="HTML"
        )
        return

    # NEWS
    if text.startswith("/news"):

        articles = get_news()

        if not articles:
            bot.send_message(
                chat_id=chat_id,
                text="📭 Chưa tìm thấy tin mới."
            )
            return

        output = "📰 <b>TIN MỚI NHẤT</b>\n\n"

        for i, article in enumerate(articles[:5], 1):
            output += format_article(article, i)
            output += "\n\n━━━━━━━━━━━━━━\n\n"

        bot.send_message(
            chat_id=chat_id,
            text=output,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    # TODAY
    if text.startswith("/today"):

        bot.send_message(
            chat_id=chat_id,
            text=make_daily_news(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    # SUBSCRIBE
    if text.startswith("/subscribe"):

        if chat_id not in subscribers:
            subscribers.append(chat_id)
            save_subscribers(subscribers)

        bot.send_message(
            chat_id=chat_id,
            text=(
                "🔔 <b>Đã bật thông báo!</b>\n\n"
                "Bạn sẽ nhận bản tin Lộc Bình mỗi ngày."
            ),
            parse_mode="HTML"
        )
        return

    # UNSUBSCRIBE
    if text.startswith("/unsubscribe"):

        if chat_id in subscribers:
            subscribers.remove(chat_id)
            save_subscribers(subscribers)

        bot.send_message(
            chat_id=chat_id,
            text="🔕 Đã tắt thông báo bản tin."
        )
        return

    # HELP
    if text.startswith("/help"):

        bot.send_message(
            chat_id=chat_id,
            text=(
                "ℹ️ <b>HƯỚNG DẪN</b>\n\n"
                "/start — Bắt đầu\n"
                "/news — Tin mới nhất\n"
                "/today — Bản tin hôm nay\n"
                "/subscribe — Nhận tin mỗi ngày\n"
                "/unsubscribe — Tắt thông báo\n"
                "/help — Trợ giúp"
            ),
            parse_mode="HTML"
        )
        return


# =========================
# KIỂM TRA TIN NHẮN
# =========================

def check_updates(bot):

    last_id = get_last_update_id()

    try:
        updates = bot.get_updates(
            offset=last_id + 1,
            timeout=5,
            allowed_updates=["message"]
        )

        newest_id = last_id

        for update in updates:

            newest_id = max(newest_id, update.update_id)

            if update.message:
                message = update.message.to_dict()
                handle_message(bot, message)

        if newest_id != last_id:
            save_last_update_id(newest_id)

    except Exception as e:
        print("Update error:", e)


# =========================
# GỬI BẢN TIN HÀNG NGÀY
# =========================

def send_daily_news(bot):

    subscribers = load_subscribers()

    if not subscribers:
        print("Chưa có người đăng ký.")
        return

    news = make_daily_news()

    for chat_id in subscribers:

        try:
            bot.send_message(
                chat_id=chat_id,
                text=news,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            time.sleep(0.2)

        except Exception as e:
            print("Send error:", chat_id, e)


# =========================
# MAIN
# =========================

def main():

    bot = Bot(TOKEN)

    # Kiểm tra message
    check_updates(bot)

    # DAILY FLAG
    now = datetime.now(VN_TZ)

    # GitHub Actions truyền biến này khi chạy bản tin
    if os.environ.get("DAILY_NEWS") == "1":
        send_daily_news(bot)

    print("Bot đã chạy xong.")


if __name__ == "__main__":
    main()
