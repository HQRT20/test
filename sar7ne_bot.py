import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
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

TOKEN = os.getenv("BOT_TOKEN", "PUT_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5561152568"))
PRIVATE_LOG_CHANNEL_ID = int(os.getenv("PRIVATE_LOG_CHANNEL_ID", "0"))
DATA_FILE = Path(os.getenv("DATA_FILE", "sar7ne_data.json"))
TIMEZONE_LABEL = os.getenv("BOT_TIMEZONE_LABEL", "Asia/Baghdad")
ADVERTISEMENT = os.getenv(
    "BOT_AD_TEXT",
    "[- فضلاً تابع قناتنا {Serø ⁞ Bots Service} 💙📿](https://t.me/SeroBots)",
)
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/SeroBots")

COMMANDS_TEXT = {
    "start": "رسالة البدء",
    "help": "عرض الأوامر والمساعدة",
    "ban": "مع الرد على الرسالة - حظر",
    "unban": "مع الرد على الرسالة - رفع الحظر",
    "unbanall": "رفع الحظر عن الجميع",
    "report": "إبلاغ",
    "link": "إدارة رابطك الخاص",
    "exit": "إلغاء الإرسال",
    "privacy": "سياسة الخصوصية",
    "termsofuse": "شروط الاستخدام",
}

HOME_TEXT = f"""اهلاً بك:

▪️ بوت صارحني

▫️ احصل على رابطك الخاص واستقبل الرسائل عبره.
▫️ عند دخول أي شخص إلى رابطك سيظهر له اسمك ومعرفك لتأكيد الجهة المستلمة.
▫️ جميع الرسائل تُسجل في قناة خاصة للإدارة مع بيانات المرسل للحماية القانونية.

⚙️ أوامر البوت - /help

{ADVERTISEMENT}
."""

ABOUT_TEXT = f"""📩 بوت صارحني

▫️ هذا الإصدار يركز على الوضوح والحماية.
▫️ المرسل يرى اسم صاحب الرابط ومعرفه قبل الإرسال.
▫️ هوية المرسل لا تُعرض للمستلم داخل المحادثة، لكنها تُحفظ في سجل إداري خاص للحماية عند الإساءة أو المطالبة بهوية المتجاوز.
▫️ يمكن لكل مستخدم إيقاف أو إعادة فتح استقبال الرسائل من خلال رابطه في أي وقت.

💡 إصدار البوت: Python Edition
👨🏻‍🔧 التحويل والتطوير: ChatGPT

{ADVERTISEMENT}
."""

HELP_TEXT = f"""اهلاً بك:

🌟 الأوامر المتاحة:

▪️ /ban — مع الرد على رسالة مصارحة لحظر صاحبها.
▫️ /unban — مع الرد على رسالة مصارحة لفك الحظر.
🔘 /unbanall — رفع الحظر عن جميع المحظورين.
⚠️ /report — الإبلاغ عن رسالة مخالفة.
🖇 /link — إنشاء وإدارة رابطك الخاص.
🔘 من لوحة الرابط — فتح أو إغلاق استقبال الرسائل بالأزرار.
🚸 /exit — الخروج من وضع الإرسال الحالي.
🔏 /privacy — سياسة الخصوصية.
📝 /termsofuse — شروط الاستخدام.

ملاحظات مهمة:
1️⃣ قبل الإرسال سيظهر للمرسل اسم صاحب الرابط ومعرفه للتأكيد.
2️⃣ إذا أغلق صاحب الرابط الاستلام، يتوقف استقبال الرسائل حتى يعيد فتحه.
3️⃣ جميع الرسائل تُحفظ في قناة خاصة للإدارة مع بيانات المرسل للحماية القانونية.

{ADVERTISEMENT}
."""

PRIVACY_TEXT = f"""*🔐 سياسة الخصوصية*

1️⃣ *هوية المرسل أمام المستلم:*
المستلم لا يرى هوية المرسل مباشرة داخل الرسالة.

2️⃣ *السجل الإداري:*
كل رسالة تُحوَّل أيضاً إلى قناة خاصة بالإدارة مع اسم المرسل ومعرفه وايديه ونص الرسالة والجهة المستلمة، وذلك للحماية عند وجود إساءة أو شكوى قانونية.

3️⃣ *بيانات التشغيل:*
نحتفظ بمعرفات المستخدمين، حالة الرابط، بيانات الحظر، والبيانات اللازمة لإيصال الرسائل والردود.

4️⃣ *التحكم بالرابط:*
يمكن لصاحب الرابط إيقاف استقبال الرسائل أو إعادة فتحه متى شاء.

▫️ استمرارك باستخدام البوت يعني موافقتك على هذه السياسة.

{ADVERTISEMENT}
."""

TERMS_TEXT = f"""*📝 شروط الاستخدام*

1️⃣ يمنع استخدام البوت للإساءة أو التهديد أو الابتزاز أو التشهير أو المحتوى المخالف.
2️⃣ كل رسالة مرسلة تُسجل في سجل إداري خاص مع بيانات المرسل للحماية والتحقق عند الحاجة.
3️⃣ يحق للإدارة حظر أي مستخدم يثبت تجاوزه للشروط.
4️⃣ لصاحب الرابط الحق في إغلاق استقبال الرسائل في أي وقت.
5️⃣ استخدامك للبوت يعني موافقتك على آلية التسجيل الإداري وعدم إساءة الاستخدام.

{ADVERTISEMENT}
."""

HEARTS = ["🩷", "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🩶", "🤍", "🤎"]
DHIKR_TEXTS = [
    "الحمد لله",
    "سبحان الله",
    "واذكر ربك إذا نسيت",
    "لا إله إلا الله",
    "لا تنسَ ذكر الله",
]

DIGIT_ENCODE_MAP = str.maketrans({"1": "x", "2": "X", "3": "S", "4": "s", "5": "P", "6": "p", "7": "K", "8": "k", "9": "A", "0": "a"})
DIGIT_DECODE_MAP = str.maketrans({"x": "1", "X": "2", "S": "3", "s": "4", "P": "5", "p": "6", "K": "7", "k": "8", "A": "9", "a": "0"})


class JSONStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = RLock()
        self.data: dict[str, dict[str, Any]] = {}
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")
        self._load()

    def _load(self) -> None:
        with self.lock:
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(self.data, dict):
                    self.data = {}
            except Exception:
                logger.exception("Failed to load store, starting fresh")
                self.data = {}

    def _save(self) -> None:
        with self.lock:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        with self.lock:
            item = self.data.get(key)
            if not item:
                return default
            expires = item.get("expires", 0)
            if expires and expires < time.time():
                self.data.pop(key, None)
                self._save()
                return default
            return item.get("value", default)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self.lock:
            self.data[key] = {
                "value": value,
                "expires": int(time.time()) + ttl if ttl else 0,
            }
            self._save()

    def delete(self, key: str) -> None:
        with self.lock:
            self.data.pop(key, None)
            self._save()

    def append_unique(self, key: str, value: Any) -> bool:
        current = self.get(key, [])
        if not isinstance(current, list):
            current = []
        if value in current:
            return False
        current.append(value)
        self.set(key, current)
        return True

    def remove_value(self, key: str, value: Any) -> bool:
        current = self.get(key, [])
        if not isinstance(current, list) or value not in current:
            return False
        current = [v for v in current if v != value]
        self.set(key, current)
        return True


store = JSONStore(DATA_FILE)


@dataclass
class AnonymousReplyMeta:
    sender_id: int
    original_message_id: int


def encode_id(value: int) -> str:
    return str(value).translate(DIGIT_ENCODE_MAP)


def decode_id(value: str) -> int:
    return int(value.translate(DIGIT_DECODE_MAP))


def report_code(length: int = 9) -> int:
    low = 10 ** (length - 1)
    high = (10 ** length) - 1
    return random.randint(low, high)


def user_display_name(user) -> str:
    parts = [user.first_name or "", user.last_name or ""]
    return " ".join(p for p in parts if p).strip() or "مستخدم"


def escape_md(text: str) -> str:
    text = text or ""
    for char in "_[]()~`>#+-=|{}.!":
        text = text.replace(char, f"\\{char}")
    return text


def make_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔐 سياسة الخصوصية", callback_data="privacy"),
                InlineKeyboardButton("📝 شروط الاستخدام", callback_data="terms"),
            ],
            [
                InlineKeyboardButton("💡 عن البوت", callback_data="about"),
                InlineKeyboardButton("⚙️ أوامر البوت", callback_data="commands"),
            ],
            [InlineKeyboardButton("🌐 إدارة رابطك", callback_data="link")],
        ]
    )


def back_keyboard(target: str = "home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=target)]])


def close_send_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚫 إلغاء إرسال الرسائل", callback_data="close_send")]]
    )


def admin_report_keyboard(reporter_id: int, reporter_message_id: int, accused_id: int, accused_message_id: int) -> InlineKeyboardMarkup:
    payload_good = f"report_ok:{encode_id(reporter_id)}:{encode_id(reporter_message_id)}"
    payload_ban = f"report_ban:{encode_id(reporter_id)}:{encode_id(reporter_message_id)}:{encode_id(accused_id)}:{encode_id(accused_message_id)}"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("نتائج سليمة ✅", callback_data=payload_good)],
            [InlineKeyboardButton("❌ مخالفة + حظر المبلغ عليه", callback_data=payload_ban)],
        ]
    )


def build_reply_callback(sender_id: int, original_message_id: int) -> str:
    return f"reply:{encode_id(sender_id)}:{encode_id(original_message_id)}"


def parse_reply_callback(data: str) -> Optional[AnonymousReplyMeta]:
    try:
        _, encoded_sender, encoded_msg = data.split(":", 2)
        return AnonymousReplyMeta(
            sender_id=decode_id(encoded_sender),
            original_message_id=decode_id(encoded_msg),
        )
    except Exception:
        return None


def extract_reply_meta(message) -> Optional[AnonymousReplyMeta]:
    if not message or not message.reply_to_message:
        return None
    markup = message.reply_to_message.reply_markup
    if not markup or not markup.inline_keyboard:
        return None
    try:
        data = markup.inline_keyboard[0][0].callback_data
    except Exception:
        return None
    if not data or not data.startswith("reply:"):
        return None
    return parse_reply_callback(data)


def sender_block_key(user_id: int) -> str:
    return f"me_blocks:{user_id}"


def send_target_key(user_id: int) -> str:
    return f"send_to:{user_id}"


def person_key(user_id: int) -> str:
    return f"person:{user_id}"


def username_key(user_id: int) -> str:
    return f"username:{user_id}"


def link_enabled_key(user_id: int) -> str:
    return f"link_enabled:{user_id}"


def pending_confirm_key(user_id: int) -> str:
    return f"pending_confirm:{user_id}"


def global_blocks() -> list[int]:
    value = store.get("global_blocks", [])
    return value if isinstance(value, list) else []


def build_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start={encode_id(user_id)}"


def is_link_enabled(user_id: int) -> bool:
    value = store.get(link_enabled_key(user_id), True)
    return bool(value)


def link_status_text(user_id: int) -> str:
    return "🟢 مفتوح" if is_link_enabled(user_id) else "🔴 مغلق"


def link_manage_keyboard(user_id: int, bot_username: str) -> InlineKeyboardMarkup:
    link = build_link(bot_username, user_id)
    active = is_link_enabled(user_id)
    toggle_button = InlineKeyboardButton(
        "🔴 إغلاق الاستلام" if active else "🟢 فتح الاستلام",
        callback_data="toggle_link:off" if active else "toggle_link:on",
    )
    return InlineKeyboardMarkup(
        [
            [toggle_button],
            [InlineKeyboardButton("🔄 تحديث الحالة", callback_data="link")],
            [InlineKeyboardButton("🔗 فتح رابطي", url=link)],
            [InlineKeyboardButton("🔙 رجوع", callback_data="home")],
        ]
    )


async def set_bot_commands(application: Application) -> None:
    commands = [BotCommand(cmd, desc) for cmd, desc in COMMANDS_TEXT.items()]
    await application.bot.set_my_commands(commands)


async def ensure_profile(update: Update) -> None:
    user = update.effective_user
    if not user:
        return
    store.set(person_key(user.id), user_display_name(user))
    store.set(username_key(user.id), user.username or "")
    if store.get(link_enabled_key(user.id)) is None:
        store.set(link_enabled_key(user.id), True)


async def reply_text(target, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None, reply_to_message_id: Optional[int] = None) -> None:
    await target.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=reply_markup,
        reply_to_message_id=reply_to_message_id,
    )


async def blocked_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False
    if user.id == ADMIN_ID:
        return False
    if user.id in global_blocks():
        await update.effective_message.reply_text(
            "▪️ أنت محظور من استخدام البوت بسبب مخالفة شروط الاستخدام.\n\n"
            "⚠️ إذا كنت ترى أن الحظر بالخطأ تواصل مع الدعم الفني.\n\n"
            f"{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🤍 الدعم الفني", url=SUPPORT_URL)]]
            ),
        )
        return True
    return False


async def send_log_message(context: ContextTypes.DEFAULT_TYPE, *, sender, recipient_id: int, recipient_name: str, recipient_username: str, text: str, kind: str, source_message_id: int) -> None:
    if not PRIVATE_LOG_CHANNEL_ID:
        return
    sender_name = escape_md(user_display_name(sender))
    sender_username = escape_md(sender.username or "لا يوجد")
    recipient_name_md = escape_md(recipient_name or "غير معروف")
    recipient_username_md = escape_md(recipient_username or "لا يوجد")
    body = escape_md(text or "(بدون نص)")
    log_text = f"""📥 *سجل رسالة جديدة*
النوع: *{escape_md(kind)}*
المرسل: [{sender_name}](tg://user?id={sender.id})
يوزر المرسل: @{sender_username}
ايدي المرسل: `{sender.id}`

المستلم: [{recipient_name_md}](tg://user?id={recipient_id})
يوزر المستلم: @{recipient_username_md}
ايدي المستلم: `{recipient_id}`
رسالة المصدر: `{source_message_id}`

النص:
```
{text or '(بدون نص)'}
```"""
    try:
        await context.bot.send_message(
            chat_id=PRIVATE_LOG_CHANNEL_ID,
            text=log_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except Exception:
        logger.exception("Failed to send moderation log")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return

    user = update.effective_user
    message = update.effective_message
    bot_username = (await context.bot.get_me()).username

    if context.args:
        code = context.args[0].strip()
        try:
            target_id = decode_id(code)
        except Exception:
            await reply_text(message, f"▪️ الرابط غير صالح.\n\n{ADVERTISEMENT}\n.")
            return

        target_name = store.get(person_key(target_id))
        target_username = store.get(username_key(target_id), "")
        if not target_name:
            await reply_text(message, f"▪️ لا يوجد شخص في الرابط الذي دخلت منه.\n\n{ADVERTISEMENT}\n.")
            return
        if user.id == target_id:
            await reply_text(message, f"▪️ لا يمكنك الإرسال لنفسك.\n\n{ADVERTISEMENT}\n.")
            return
        if not is_link_enabled(target_id):
            await reply_text(message, f"▪️ هذا المستخدم أغلق استقبال الرسائل حالياً.\n\n{ADVERTISEMENT}\n.")
            return
        blocked_by_target = store.get(sender_block_key(target_id), [])
        if user.id in blocked_by_target:
            await reply_text(message, f"▪️ أنت محظور من الدخول إلى رابط هذا المستخدم.\n\n{ADVERTISEMENT}\n.")
            return

        store.set(pending_confirm_key(user.id), target_id)
        await reply_text(
            message,
            "▪️ تأكيد جهة الاستلام\n\n"
            f"الاسم: *{escape_md(target_name)}*\n"
            f"المعرف: @{escape_md(target_username or 'لا يوجد')}\n"
            f"الايدي: `{target_id}`\n\n"
            "▫️ إذا كنت تريد الإرسال لهذا الشخص اضغط *✅ تأكيد الدخول للإرسال*.\n"
            "▫️ سيتم تسجيل رسالتك في قناة خاصة بالإدارة مع بياناتك للحماية عند الإساءة.\n\n"
            f"{ADVERTISEMENT}\n.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("✅ تأكيد الدخول للإرسال", callback_data=f"confirm_send:{encode_id(target_id)}")],
                    [InlineKeyboardButton("❌ إلغاء", callback_data="home")],
                ]
            ),
        )
        return

    await reply_text(message, HOME_TEXT, reply_markup=make_home_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    await reply_text(update.effective_message, HELP_TEXT, reply_markup=back_keyboard())


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    bot_username = (await context.bot.get_me()).username
    link = build_link(bot_username, update.effective_user.id)
    await reply_text(
        update.effective_message,
        f"▪️ الرابط الخاص بك:\n\n▫️ {link}\n\n"
        f"▫️ حالة الاستلام الحالية: {link_status_text(update.effective_user.id)}\n"
        "▫️ يمكنك فتح أو إغلاق الاستلام في أي وقت.\n\n"
        f"{ADVERTISEMENT}\n.",
        reply_markup=link_manage_keyboard(),
    )


async def togglelink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    current = is_link_enabled(update.effective_user.id)
    store.set(link_enabled_key(update.effective_user.id), not current)
    if not current:
        text = "🟢 تم فتح استقبال الرسائل من رابطك بنجاح."
    else:
        text = "🔴 تم إغلاق استقبال الرسائل من رابطك بنجاح."
        store.delete(send_target_key(update.effective_user.id))
    await reply_text(update.effective_message, f"{text}\n\n{ADVERTISEMENT}\n.", reply_markup=link_manage_keyboard())


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    await reply_text(update.effective_message, PRIVACY_TEXT, reply_markup=back_keyboard("about"))


async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    await reply_text(update.effective_message, TERMS_TEXT, reply_markup=back_keyboard("about"))


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    store.delete(send_target_key(update.effective_user.id))
    store.delete(pending_confirm_key(update.effective_user.id))
    await reply_text(
        update.effective_message,
        "✅ تم إلغاء الإرسال.\n"
        "▪️ لن تتمكن من إرسال أي رسالة الآن.\n"
        "▫️ للعودة للإرسال ادخل إلى رابط العضو مرة أخرى.\n\n"
        f"{ADVERTISEMENT}\n.",
        reply_markup=back_keyboard(),
    )


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    meta = extract_reply_meta(update.effective_message)
    if not meta:
        await reply_text(update.effective_message, f"▪️ استخدم /ban بالرد على رسالة مصارحة فقط.\n\n{ADVERTISEMENT}\n.")
        return
    added = store.append_unique(sender_block_key(update.effective_user.id), meta.sender_id)
    if not added:
        await reply_text(update.effective_message, f"🚫 صاحب هذه الرسالة محظور بالفعل.\n\n{ADVERTISEMENT}\n.")
        return

    if store.get(send_target_key(meta.sender_id)) == update.effective_user.id:
        store.delete(send_target_key(meta.sender_id))

    await reply_text(update.effective_message, f"🚷 تم حظر صاحب هذه الرسالة بنجاح.\n\n{ADVERTISEMENT}\n.")
    try:
        await context.bot.send_message(
            chat_id=meta.sender_id,
            text="▪️ لقد تم حظرك من إرسال الرسائل لهذا المستخدم.\n\n" + ADVERTISEMENT + "\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except Exception:
        logger.info("Could not notify banned sender %s", meta.sender_id)


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    meta = extract_reply_meta(update.effective_message)
    if not meta:
        await reply_text(update.effective_message, f"▪️ استخدم /unban بالرد على رسالة مصارحة فقط.\n\n{ADVERTISEMENT}\n.")
        return
    removed = store.remove_value(sender_block_key(update.effective_user.id), meta.sender_id)
    if removed:
        await reply_text(update.effective_message, f"⭕️ تم رفع الحظر عن صاحب هذه الرسالة.\n\n{ADVERTISEMENT}\n.")
    else:
        await reply_text(update.effective_message, f"✅ صاحب الرسالة غير محظور أساساً.\n\n{ADVERTISEMENT}\n.")


async def unbanall_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    blocked = store.get(sender_block_key(update.effective_user.id), [])
    count = len(blocked) if isinstance(blocked, list) else 0
    if count == 0:
        await reply_text(update.effective_message, f"▫️ لا يوجد لديك أي شخص محظور.\n\n{ADVERTISEMENT}\n.")
        return
    await reply_text(
        update.effective_message,
        f"▪️ يوجد لديك {{ {count} }} شخص محظور.\n"
        "▫️ هل أنت متأكد من رفع الحظر عن الجميع؟\n\n"
        f"{ADVERTISEMENT}\n.",
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("❌ لا", callback_data="home"),
                InlineKeyboardButton("✅ نعم", callback_data="unbanall_confirm"),
            ]]
        ),
    )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return
    message = update.effective_message
    meta = extract_reply_meta(message)
    if not meta:
        await reply_text(message, f"▪️ استخدم /report بالرد على الرسالة المخالفة.\n\n{ADVERTISEMENT}\n.")
        return

    target_name = store.get(person_key(meta.sender_id), "غير معروف")
    target_username = store.get(username_key(meta.sender_id), "") or "لا يوجد"
    report_id = report_code()

    replied_text = message.reply_to_message.text or "(بدون نص)"
    match = re.search(r"----\s*(.*?)\s*----", replied_text, flags=re.S)
    reported_message_text = match.group(1).strip() if match else replied_text.strip()

    await reply_text(
        message,
        f"🚨 شكراً لك! تم استلام بلاغك.\n"
        f"🔘 كود البلاغ للمراجعة [#report_{report_id}]\n"
        "♻️ ستتم مراجعة البلاغ من الإدارة.\n\n"
        f"{ADVERTISEMENT}\n.",
    )

    admin_text = f"""🚨 بلاغ رقم `#{report_id}`

👤 معلومات المبلّغ:
الاسم: [{escape_md(user_display_name(update.effective_user))}](tg://user?id={update.effective_user.id})
الايدي: `{update.effective_user.id}`
المعرف: @{escape_md(update.effective_user.username or 'لايوجد')}

🧑‍💼 معلومات المبلّغ عليه:
الاسم: [{escape_md(target_name)}](tg://user?id={meta.sender_id})
الايدي: `{meta.sender_id}`
المعرف: @{escape_md(target_username)}

📃 الرسالة المبلغ عليها:
```
{reported_message_text}
```"""
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=admin_report_keyboard(
            update.effective_user.id,
            message.message_id,
            meta.sender_id,
            meta.original_message_id,
        ),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await ensure_profile(update)

    if query.data == "home":
        await query.edit_message_text(HOME_TEXT, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=make_home_keyboard())
        return
    if query.data == "about":
        await query.edit_message_text(ABOUT_TEXT, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=back_keyboard())
        return
    if query.data == "commands":
        await query.edit_message_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=back_keyboard())
        return
    if query.data == "privacy":
        await query.edit_message_text(PRIVACY_TEXT, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=back_keyboard("about"))
        return
    if query.data == "terms":
        await query.edit_message_text(TERMS_TEXT, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=back_keyboard("about"))
        return
    if query.data == "link":
        bot_username = (await context.bot.get_me()).username
        link = build_link(bot_username, query.from_user.id)
        await query.edit_message_text(
            f"▪️ الرابط الخاص بك:\n\n▫️ {link}\n\n"
            f"▫️ حالة الاستلام الحالية: {link_status_text(query.from_user.id)}\n"
            "▫️ يمكنك فتح أو إغلاق الاستلام في أي وقت.\n\n"
            f"{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=link_manage_keyboard(),
        )
        return
    if query.data.startswith("toggle_link:"):
        _, mode = query.data.split(":", 1)
        enabled = mode == "on"
        store.set(link_enabled_key(query.from_user.id), enabled)
        if not enabled:
            store.delete(send_target_key(query.from_user.id))
            status_text = "🔴 تم إغلاق استقبال الرسائل من رابطك."
        else:
            status_text = "🟢 تم فتح استقبال الرسائل من رابطك."
        bot_username = (await context.bot.get_me()).username
        link = build_link(bot_username, query.from_user.id)
        await query.edit_message_text(
            f"{status_text}\n\n▫️ رابطك: {link}\n▫️ الحالة الحالية: {link_status_text(query.from_user.id)}\n\n{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=link_manage_keyboard(),
        )
        return
    if query.data.startswith("confirm_send:"):
        target_id = decode_id(query.data.split(":", 1)[1])
        pending = store.get(pending_confirm_key(query.from_user.id))
        if pending != target_id:
            await query.edit_message_text(
                f"▪️ انتهت صلاحية التأكيد. ادخل إلى الرابط مرة أخرى.\n\n{ADVERTISEMENT}\n.",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=back_keyboard(),
            )
            return
        if not is_link_enabled(target_id):
            store.delete(pending_confirm_key(query.from_user.id))
            await query.edit_message_text(
                f"▪️ هذا المستخدم أغلق استقبال الرسائل حالياً.\n\n{ADVERTISEMENT}\n.",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=back_keyboard(),
            )
            return
        blocked_by_target = store.get(sender_block_key(target_id), [])
        if query.from_user.id in blocked_by_target:
            store.delete(pending_confirm_key(query.from_user.id))
            await query.edit_message_text(
                f"▪️ أنت محظور من مراسلة هذا المستخدم.\n\n{ADVERTISEMENT}\n.",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=back_keyboard(),
            )
            return
        store.set(send_target_key(query.from_user.id), target_id)
        store.delete(pending_confirm_key(query.from_user.id))
        await query.edit_message_text(
            "✅ تم تفعيل وضع الإرسال.\n"
            "▫️ اكتب الآن رسالتك وسيتم إرسالها للطرف الآخر.\n"
            "▫️ هوية المرسل لا تظهر للمستلم داخل المحادثة، لكنها محفوظة في السجل الإداري الخاص.\n\n"
            f"{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=close_send_keyboard(),
        )
        return
    if query.data == "close_send":
        store.delete(send_target_key(query.from_user.id))
        store.delete(pending_confirm_key(query.from_user.id))
        await query.edit_message_text(
            "✅ تم إلغاء الإرسال.\n"
            "▪️ لن تتمكن من إرسال أي رسالة الآن.\n"
            "▫️ إذا أردت معاودة الإرسال ادخل للرابط مرة أخرى.\n\n"
            f"{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=back_keyboard(),
        )
        return
    if query.data == "unbanall_confirm":
        store.delete(sender_block_key(query.from_user.id))
        await query.edit_message_text(
            f"▫️ تم رفع الحظر عن جميع المحظورين بنجاح.\n\n{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=back_keyboard(),
        )
        return
    if query.data.startswith("reply:"):
        meta = parse_reply_callback(query.data)
        if meta:
            await query.answer(
                text="💡 يمكنك الرد على هذه الرسالة مباشرة.",
                show_alert=True,
            )
        return
    if query.data.startswith("report_ok:"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("هذا الخيار للمشرف فقط", show_alert=True)
            return
        _, reporter_id_encoded, reporter_msg_encoded = query.data.split(":", 2)
        reporter_id = decode_id(reporter_id_encoded)
        reporter_msg_id = decode_id(reporter_msg_encoded)
        await context.bot.send_message(
            chat_id=reporter_id,
            text="✅ تم فحص الرسالة ولم يتم العثور على مخالفة.\n\n" + ADVERTISEMENT + "\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_to_message_id=reporter_msg_id,
        )
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بلاغ سليم ✅", callback_data="noop")]])
        )
        return
    if query.data.startswith("report_ban:"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("هذا الخيار للمشرف فقط", show_alert=True)
            return
        _, reporter_id_encoded, reporter_msg_encoded, accused_id_encoded, accused_msg_encoded = query.data.split(":", 4)
        reporter_id = decode_id(reporter_id_encoded)
        reporter_msg_id = decode_id(reporter_msg_encoded)
        accused_id = decode_id(accused_id_encoded)
        accused_msg_id = decode_id(accused_msg_encoded)
        store.append_unique("global_blocks", accused_id)

        try:
            await context.bot.send_message(
                chat_id=accused_id,
                text="⚠️ تم حظر حسابك من استخدام البوت بسبب مخالفة الشروط.\n\n" + ADVERTISEMENT + "\n.",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_to_message_id=accused_msg_id,
            )
        except Exception:
            logger.info("Could not notify globally banned user %s", accused_id)

        await context.bot.send_message(
            chat_id=reporter_id,
            text="🚨 تم التحقق من البلاغ، وتبين وجود مخالفة وتم اتخاذ الإجراء المناسب.\n\n" + ADVERTISEMENT + "\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_to_message_id=reporter_msg_id,
        )
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("تم حظر المستخدم ⚠️", callback_data="noop")]]
            )
        )
        return

    await query.answer(random.choice(HEARTS) + " " + random.choice(DHIKR_TEXTS))


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_profile(update)
    if await blocked_guard(update, context):
        return

    message = update.effective_message
    text = message.text or ""
    user = update.effective_user
    user_id = user.id

    if text.startswith("/"):
        return

    reply_meta = extract_reply_meta(message)
    if reply_meta:
        await handle_anonymous_reply(update, context, reply_meta)
        return

    target_id = store.get(send_target_key(user_id))
    if not target_id:
        return

    if not is_link_enabled(target_id):
        store.delete(send_target_key(user_id))
        await message.reply_text(
            f"▪️ هذا المستخدم أغلق استقبال الرسائل حالياً.\n\n{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    blocked_by_target = store.get(sender_block_key(target_id), [])
    if user_id in blocked_by_target:
        store.delete(send_target_key(user_id))
        await message.reply_text(
            f"▪️ أنت محظور من مراسلة هذا المستخدم.\n\n{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    recipient_name = store.get(person_key(target_id), "مستخدم")
    recipient_username = store.get(username_key(target_id), "")

    await message.reply_text(
        f"✅ تم إرسال رسالتك بنجاح.\n\n{ADVERTISEMENT}\n.",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )

    outbound = (
        "💌 وصلتك رسالة جديدة\n"
        f"⏱ وقت الرسالة: {time.strftime('%Y/%m/%d - %I:%M:%S %p')} ({TIMEZONE_LABEL})\n"
        "----\n"
        f"{text}\n"
        "----\n\n"
        f"{ADVERTISEMENT}\n."
    )
    await context.bot.send_message(
        chat_id=target_id,
        text=outbound,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("💡 يمكنك الرد على هذه الرسالة", callback_data=build_reply_callback(user_id, message.message_id))]]
        ),
    )
    await send_log_message(
        context,
        sender=user,
        recipient_id=target_id,
        recipient_name=recipient_name,
        recipient_username=recipient_username,
        text=text,
        kind="رسالة جديدة",
        source_message_id=message.message_id,
    )


async def handle_anonymous_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, meta: AnonymousReplyMeta) -> None:
    message = update.effective_message
    replier = update.effective_user
    replier_id = replier.id
    receiver_id = meta.sender_id
    receiver_name = store.get(person_key(receiver_id), "مستخدم")
    receiver_username = store.get(username_key(receiver_id), "")
    target_link = build_link((await context.bot.get_me()).username, replier_id)

    sent_primary = None
    sent_secondary = None
    try:
        sent_primary = await context.bot.send_message(
            chat_id=receiver_id,
            text=message.text,
            reply_to_message_id=meta.original_message_id,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💌 وصلتك رسالة جديدة", callback_data=build_reply_callback(replier_id, message.message_id))]]
            ),
        )

        if store.get(send_target_key(receiver_id)) != replier_id:
            sent_secondary = await context.bot.send_message(
                chat_id=receiver_id,
                text=(
                    "❗️ هذه الرسالة وصلتك من شخص سبق أن راسلته من قبل لكنه خرج من رابطك.\n"
                    f"🚪 [اضغط هنا إذا أردت إرسال الرسائل له مرة أخرى]({target_link})\n\n"
                    f"{ADVERTISEMENT}\n."
                ),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_to_message_id=sent_primary.message_id,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔘 الدخول مرة أخرى", url=target_link)]]
                ),
            )

        buttons = []
        if sent_primary:
            payload = f"recall:{receiver_id}:{sent_primary.message_id}:{sent_secondary.message_id if sent_secondary else 0}"
            buttons.append([InlineKeyboardButton("🗑 استرداد الرد", callback_data=payload)])

        await message.reply_text(
            f"✅ تم الرد على هذه الرسالة بنجاح.\n\n{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )
        await send_log_message(
            context,
            sender=replier,
            recipient_id=receiver_id,
            recipient_name=receiver_name,
            recipient_username=receiver_username,
            text=message.text or "",
            kind="رد على رسالة",
            source_message_id=message.message_id,
        )
    except Exception:
        logger.exception("Failed to forward anonymous reply")
        await message.reply_text(
            f"❌ تعذر الرد على هذه الرسالة.\nقد يكون المستخدم حظر البوت أو أن الرسالة الأصلية لم تعد قابلة للرد.\n\n{ADVERTISEMENT}\n.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )


async def handle_recall_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, chat_id, msg1, msg2 = query.data.split(":", 3)
    chat_id_i = int(chat_id)
    for msg_id in (int(msg1), int(msg2)):
        if msg_id > 0:
            try:
                await context.bot.delete_message(chat_id=chat_id_i, message_id=msg_id)
            except Exception:
                logger.info("Could not delete message %s in %s", msg_id, chat_id_i)
    await query.edit_message_text(
        f"🗑 تم استرداد الرد بنجاح.\n\n{ADVERTISEMENT}\n.",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.callback_query.data or ""
    if data.startswith("recall:"):
        await handle_recall_callback(update, context)
    else:
        await handle_callback(update, context)


async def post_init(application: Application) -> None:
    await set_bot_commands(application)


def build_application() -> Application:
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("unbanall", unbanall_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("togglelink", togglelink_command))
    app.add_handler(CommandHandler("exit", exit_command))
    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CommandHandler("termsofuse", terms_command))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    return app


def main() -> None:
    if not TOKEN or TOKEN == "PUT_BOT_TOKEN_HERE":
        raise RuntimeError("ضع توكن البوت في المتغير BOT_TOKEN قبل التشغيل")
    application = build_application()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
