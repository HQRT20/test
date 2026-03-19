import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

from flask import Flask
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("sar7ne")

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PRIVATE_LOG_CHANNEL_ID = int(os.getenv("PRIVATE_LOG_CHANNEL_ID", "0"))
DATA_FILE = Path(os.getenv("DATA_FILE", "sar7ne_data.json"))
PORT = int(os.getenv("PORT", "10000"))
TIME_LABEL = os.getenv("TIME_LABEL", "Asia/Baghdad")

app = Flask(__name__)


@app.get("/")
def home() -> str:
    return "Sar7ne bot is running"


class Store:
    def __init__(self, path: Path):
        self.path = path
        if not self.path.exists():
            self.path.write_text(json.dumps({"users": {}, "global_bans": []}, ensure_ascii=False), encoding="utf-8")
        self.data = self._read()

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"users": {}, "global_bans": []}
            data.setdefault("users", {})
            data.setdefault("global_bans", [])
            return data
        except Exception:
            logger.exception("Failed to read data file")
            return {"users": {}, "global_bans": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def user(self, user_id: int) -> dict[str, Any]:
        key = str(user_id)
        users = self.data.setdefault("users", {})
        users.setdefault(
            key,
            {
                "name": "",
                "username": "",
                "link_open": True,
                "blocked_senders": [],
                "send_to": None,
                "pending_target": None,
            },
        )
        return users[key]

    def global_bans(self) -> list[int]:
        return [int(x) for x in self.data.get("global_bans", [])]

    def add_global_ban(self, user_id: int) -> None:
        bans = self.data.setdefault("global_bans", [])
        if user_id not in bans:
            bans.append(user_id)
            self.save()

    def remove_global_ban(self, user_id: int) -> bool:
        bans = self.data.setdefault("global_bans", [])
        if user_id in bans:
            bans.remove(user_id)
            self.save()
            return True
        return False

    def clear_global_bans(self) -> None:
        self.data["global_bans"] = []
        self.save()


store = Store(DATA_FILE)

COMMANDS = [
    BotCommand("start", "بدء البوت"),
    BotCommand("help", "الأوامر"),
    BotCommand("link", "رابطك ولوحة التحكم"),
    BotCommand("exit", "إلغاء الإرسال"),
    BotCommand("ban", "حظر مرسل بالرد على رسالته"),
    BotCommand("unban", "فك حظر مرسل بالرد على رسالته"),
    BotCommand("unbanall", "فك الحظر عن الجميع"),
    BotCommand("report", "إبلاغ عن رسالة"),
    BotCommand("privacy", "سياسة الخصوصية"),
    BotCommand("termsofuse", "شروط الاستخدام"),
]

HOME_TEXT = (
    "اهلاً بك في بوت صارحني\n\n"
    "• لكل مستخدم رابط خاص\n"
    "• قبل الإرسال يظهر اسم صاحب الرابط ومعرفه للتأكيد\n"
    "• كل رسالة تُسجل في قناة خاصة مع اسم المرسل ويوزره وآيديه للحماية\n"
    "• صاحب الرابط يقدر يفتح أو يغلق الاستلام بالأزرار\n\n"
    "استخدم /link للحصول على الرابط ولوحة التحكم."
)

HELP_TEXT = (
    "الأوامر المتاحة:\n\n"
    "/link - رابطك ولوحة التحكم\n"
    "/exit - إلغاء وضع الإرسال\n"
    "/ban - حظر مرسل بالرد على رسالة مجهولة\n"
    "/unban - فك حظر مرسل بالرد على رسالة مجهولة\n"
    "/unbanall - فك حظر الجميع\n"
    "/report - إرسال بلاغ إلى الإدارة\n"
    "/privacy - سياسة الخصوصية\n"
    "/termsofuse - شروط الاستخدام"
)

PRIVACY_TEXT = (
    "سياسة الخصوصية:\n\n"
    "1) المستلم لا يرى هوية المرسل داخل الرسالة.\n"
    "2) الإدارة تسجل كل رسالة في قناة خاصة مع اسم المرسل ويوزره وآيديه ونص الرسالة والجهة المستلمة.\n"
    "3) هذا التسجيل موجود للحماية في حال الإساءة أو الطلب القانوني أو الشكوى.\n"
    "4) يحق لصاحب الرابط إيقاف استقبال الرسائل متى شاء."
)

TERMS_TEXT = (
    "شروط الاستخدام:\n\n"
    "1) يمنع التهديد أو الابتزاز أو التشهير أو الإساءة.\n"
    "2) كل رسالة تُسجل إدارياً مع بيانات المرسل.\n"
    "3) يحق للإدارة حظر أي مستخدم مخالف.\n"
    "4) استخدامك للبوت يعني موافقتك على هذه الآلية."
)


def ensure_user(user) -> dict[str, Any]:
    data = store.user(user.id)
    data["name"] = display_name(user)
    data["username"] = user.username or ""
    store.save()
    return data



def display_name(user) -> str:
    full = " ".join(part for part in [user.first_name or "", user.last_name or ""] if part).strip()
    return full or "مستخدم"



def build_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start={user_id}"



def link_keyboard(user_id: int, bot_username: str) -> InlineKeyboardMarkup:
    user_data = store.user(user_id)
    open_now = user_data.get("link_open", True)
    toggle_text = "🔒 إغلاق الاستلام" if open_now else "🔓 فتح الاستلام"
    toggle_data = "link_close" if open_now else "link_open"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(toggle_text, callback_data=toggle_data)],
            [InlineKeyboardButton("🔄 تحديث الحالة", callback_data="show_link")],
            [InlineKeyboardButton("🔗 فتح رابطي", url=build_link(bot_username, user_id))],
        ]
    )



def confirm_keyboard(target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data=f"confirm_send:{target_id}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")],
        ]
    )



def reply_button(sender_id: int, original_message_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("↩️ الرد على هذه الرسالة", callback_data=f"replyto:{sender_id}:{original_message_id}")]]
    )



def status_text(user_id: int) -> str:
    return "🟢 مفتوح" if store.user(user_id).get("link_open", True) else "🔴 مغلق"



def extract_original_sender_id(message) -> Optional[int]:
    if not message or not message.reply_to_message:
        return None
    reply_markup = message.reply_to_message.reply_markup
    if not reply_markup or not reply_markup.inline_keyboard:
        return None
    try:
        data = reply_markup.inline_keyboard[0][0].callback_data
    except Exception:
        return None
    if not data or not data.startswith("replyto:"):
        return None
    parts = data.split(":")
    if len(parts) != 3:
        return None
    try:
        return int(parts[1])
    except Exception:
        return None


async def send_to_log(context: ContextTypes.DEFAULT_TYPE, sender, recipient_id: int, text: str, kind: str) -> None:
    if not PRIVATE_LOG_CHANNEL_ID:
        return
    recipient = store.user(recipient_id)
    log_text = (
        f"📥 {kind}\n\n"
        f"المرسل: {display_name(sender)}\n"
        f"يوزر المرسل: @{sender.username or 'بدون_يوزر'}\n"
        f"ايدي المرسل: {sender.id}\n\n"
        f"المستلم: {recipient.get('name') or 'مستخدم'}\n"
        f"يوزر المستلم: @{recipient.get('username') or 'بدون_يوزر'}\n"
        f"ايدي المستلم: {recipient_id}\n\n"
        f"النص:\n{text}"
    )
    try:
        await context.bot.send_message(chat_id=PRIVATE_LOG_CHANNEL_ID, text=log_text)
    except Exception:
        logger.exception("Failed to send log message")


async def is_blocked(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in store.global_bans() and user.id != ADMIN_ID)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)

    if await is_blocked(update):
        await update.effective_message.reply_text("أنت محظور من استخدام البوت.")
        return

    if context.args:
        try:
            target_id = int(context.args[0])
        except Exception:
            await update.effective_message.reply_text("الرابط غير صالح.")
            return

        if target_id == user.id:
            await update.effective_message.reply_text("لا يمكنك مراسلة نفسك.")
            return

        target = store.user(target_id)
        if not target.get("name"):
            await update.effective_message.reply_text("هذا الرابط غير صالح أو غير مفعّل.")
            return
        if not target.get("link_open", True):
            await update.effective_message.reply_text("هذا المستخدم أغلق استقبال الرسائل حالياً.")
            return
        if user.id in target.get("blocked_senders", []):
            await update.effective_message.reply_text("أنت محظور من مراسلة هذا المستخدم.")
            return

        sender_data = store.user(user.id)
        sender_data["pending_target"] = target_id
        store.save()

        await update.effective_message.reply_text(
            "تأكيد جهة الاستلام\n\n"
            f"الاسم: {target.get('name') or 'مستخدم'}\n"
            f"اليوزر: @{target.get('username') or 'بدون_يوزر'}\n"
            f"الايدي: {target_id}\n\n"
            "بالضغط على التأكيد فأنت تفهم أن الرسالة ستصل لهذا الشخص، "
            "كما سيتم تسجيل بياناتك في قناة خاصة للإدارة عند الإرسال.",
            reply_markup=confirm_keyboard(target_id),
        )
        return

    await update.effective_message.reply_text(HOME_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update.effective_user)
    await update.effective_message.reply_text(HELP_TEXT)


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update.effective_user)
    await update.effective_message.reply_text(PRIVACY_TEXT)


async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ensure_user(update.effective_user)
    await update.effective_message.reply_text(TERMS_TEXT)


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)
    bot_username = (await context.bot.get_me()).username
    await update.effective_message.reply_text(
        f"رابطك الخاص:\n{build_link(bot_username, user.id)}\n\n"
        f"حالة الاستلام: {status_text(user.id)}\n"
        "يمكنك التحكم عبر الأزرار أدناه.",
        reply_markup=link_keyboard(user.id, bot_username),
    )


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = store.user(update.effective_user.id)
    user_data["send_to"] = None
    user_data["pending_target"] = None
    store.save()
    await update.effective_message.reply_text("تم إلغاء وضع الإرسال.")


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)
    message = update.effective_message
    sender_id = extract_original_sender_id(message)
    if not sender_id:
        await message.reply_text("استخدم /ban بالرد على رسالة مجهولة وصلتك من البوت.")
        return
    my_data = store.user(user.id)
    if sender_id not in my_data["blocked_senders"]:
        my_data["blocked_senders"].append(sender_id)
        store.save()
    await message.reply_text("تم حظر هذا المرسل من مراسلتك.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)
    message = update.effective_message
    sender_id = extract_original_sender_id(message)
    if not sender_id:
        await message.reply_text("استخدم /unban بالرد على رسالة مجهولة وصلتك من البوت.")
        return
    my_data = store.user(user.id)
    if sender_id in my_data["blocked_senders"]:
        my_data["blocked_senders"].remove(sender_id)
        store.save()
        await message.reply_text("تم فك الحظر عن هذا المرسل.")
    else:
        await message.reply_text("هذا المرسل ليس محظوراً لديك.")


async def unbanall_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    my_data = store.user(update.effective_user.id)
    my_data["blocked_senders"] = []
    store.save()
    await update.effective_message.reply_text("تم فك الحظر عن جميع المرسلين المحظورين لديك.")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)
    message = update.effective_message
    if not message.reply_to_message:
        await message.reply_text("استخدم /report بالرد على الرسالة التي تريد الإبلاغ عنها.")
        return
    if not ADMIN_ID:
        await message.reply_text("لم يتم ضبط ADMIN_ID بعد.")
        return
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "بلاغ جديد\n\n"
            f"المبلّغ: {display_name(user)}\n"
            f"يوزر المبلّغ: @{user.username or 'بدون_يوزر'}\n"
            f"ايدي المبلّغ: {user.id}\n\n"
            f"نص الرسالة المبلّغ عنها:\n{message.reply_to_message.text or '(لا يوجد نص)'}"
        ),
    )
    await message.reply_text("تم إرسال البلاغ إلى الإدارة.")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    ensure_user(user)

    if query.data == "cancel_send":
        user_data = store.user(user.id)
        user_data["pending_target"] = None
        user_data["send_to"] = None
        store.save()
        await query.edit_message_text("تم الإلغاء.")
        return

    if query.data in {"link_open", "link_close", "show_link"}:
        user_data = store.user(user.id)
        if query.data == "link_open":
            user_data["link_open"] = True
            store.save()
        elif query.data == "link_close":
            user_data["link_open"] = False
            store.save()
        bot_username = (await context.bot.get_me()).username
        await query.edit_message_text(
            f"رابطك الخاص:\n{build_link(bot_username, user.id)}\n\n"
            f"حالة الاستلام: {status_text(user.id)}\n"
            "يمكنك التحكم عبر الأزرار أدناه.",
            reply_markup=link_keyboard(user.id, bot_username),
        )
        return

    if query.data.startswith("confirm_send:"):
        target_id = int(query.data.split(":", 1)[1])
        user_data = store.user(user.id)
        user_data["send_to"] = target_id
        user_data["pending_target"] = None
        store.save()
        await query.edit_message_text(
            "تم التفعيل.\n"
            "أرسل الآن رسالتك، وستصل إلى هذا الشخص.\n"
            "عند الرغبة بالإلغاء استخدم /exit."
        )
        return

    if query.data.startswith("replyto:"):
        await query.answer("رد على هذه الرسالة مباشرة وسيصل ردك للطرف الآخر.", show_alert=True)
        return


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)

    if await is_blocked(update):
        await update.effective_message.reply_text("أنت محظور من استخدام البوت.")
        return

    message = update.effective_message
    text = message.text or ""
    if text.startswith("/"):
        return

    reply_sender_id = extract_original_sender_id(message)
    if reply_sender_id:
        try:
            sent = await context.bot.send_message(
                chat_id=reply_sender_id,
                text=f"↩️ وصلك رد جديد:\n\n{text}",
                reply_markup=reply_button(user.id, message.message_id),
            )
            await send_to_log(context, user, reply_sender_id, text, "رد على رسالة")
            await message.reply_text("تم إرسال الرد بنجاح.")
        except Exception:
            logger.exception("Failed to forward reply")
            await message.reply_text("تعذر إرسال الرد.")
        return

    user_data = store.user(user.id)
    target_id = user_data.get("send_to")
    if not target_id:
        return

    target = store.user(target_id)
    if not target.get("link_open", True):
        user_data["send_to"] = None
        store.save()
        await message.reply_text("هذا المستخدم أغلق استقبال الرسائل حالياً.")
        return
    if user.id in target.get("blocked_senders", []):
        user_data["send_to"] = None
        store.save()
        await message.reply_text("أنت محظور من مراسلة هذا المستخدم.")
        return

    sent_msg = await context.bot.send_message(
        chat_id=target_id,
        text=(
            "💌 وصلك رسالة جديدة\n"
            f"الوقت: {time.strftime('%Y/%m/%d - %I:%M:%S %p')} ({TIME_LABEL})\n\n"
            f"{text}"
        ),
        reply_markup=reply_button(user.id, message.message_id),
    )
    await send_to_log(context, user, target_id, text, "رسالة جديدة")
    await message.reply_text("تم إرسال رسالتك بنجاح.")


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(COMMANDS)



def build_application() -> Application:
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_TOKEN":
        raise RuntimeError("BOT_TOKEN is not set")
    return (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )



def run_web() -> None:
    app.run(host="0.0.0.0", port=PORT)



def main() -> None:
    application = build_application()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("exit", exit_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("unbanall", unbanall_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("privacy", privacy_command))
    application.add_handler(CommandHandler("termsofuse", terms_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    threading.Thread(target=run_web, daemon=True).start()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
