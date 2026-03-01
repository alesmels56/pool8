"""
bot/ui.py — Single Persistent Message navigation.

Strategy:
  • answer_and_update (callback context): ALWAYS edits query.message directly.
    This is the message the user currently sees (it has the buttons they clicked).
    We never look up a stored ID here — we use what Telegram already told us.
  • update_menu (non-callback / ConversationHandler text steps): edits the stored
    menu_msg_id if available, otherwise sends a fresh message.
  • Both functions keep menu_msg_id/menu_msg_type in sync after every edit.
"""
import logging
from typing import Optional

from telegram import Bot, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# ─── Public helpers ────────────────────────────────────────────────────────────

async def answer_and_update(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
    media_file_id: Optional[str] = None,
    media_type: Optional[str] = None,  # "photo" | "video"
) -> Optional[Message]:
    """
    Answer the callback query (removes spinner) then EDIT the message that
    contains the button the user just pressed (query.message).

    This is the ONLY correct approach for callbacks: we always know exactly
    which message to edit because Telegram tells us via query.message.
    """
    try:
        await query.answer()
    except Exception:
        pass

    msg = query.message
    chat_id = msg.chat_id
    msg_id = msg.message_id
    ud = context.user_data
    target_type = media_type if media_file_id else "text"
    current_type = "text" if msg.text else ("photo" if msg.photo else ("video" if msg.video else "text"))
    bot: Bot = context.bot

    # ── Same type: edit in place ────────────────────────────────────────────
    if current_type == target_type:
        try:
            if target_type == "text":
                edited = await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            else:
                edited = await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=msg_id,
                    caption=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            ud["menu_msg_id"] = msg_id
            ud["menu_msg_type"] = target_type
            return edited
        except Exception as e:
            logger.debug(f"answer_and_update: edit failed ({e}), sending fresh")

    # ── Type mismatch (text→media or media→text): delete old, send new ─────
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass

    return await _send_fresh(bot, ud, chat_id, text, parse_mode, reply_markup, media_file_id, media_type)


async def update_menu(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
    media_file_id: Optional[str] = None,
    media_type: Optional[str] = None,
) -> Optional[Message]:
    """
    Edit the stored persistent menu message (used in non-callback contexts,
    e.g. ConversationHandler text steps).

    If no stored message exists, or the edit fails, sends a fresh message.
    """
    ud = context.user_data
    bot: Bot = context.bot
    current_msg_id: Optional[int] = ud.get("menu_msg_id")
    current_type: str = ud.get("menu_msg_type", "text")
    target_type = media_type if media_file_id else "text"

    # ── Edit in place if type unchanged ────────────────────────────────────
    if current_msg_id and current_type == target_type:
        try:
            if target_type == "text":
                msg = await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=current_msg_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            else:
                msg = await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=current_msg_id,
                    caption=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            ud["menu_msg_id"] = current_msg_id
            ud["menu_msg_type"] = target_type
            return msg
        except Exception as e:
            logger.debug(f"update_menu: edit failed ({e}), sending fresh")
            current_msg_id = None

    # ── Type changed: delete old first ─────────────────────────────────────
    if current_msg_id and current_type != target_type:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=current_msg_id)
        except Exception:
            pass

    return await _send_fresh(bot, ud, chat_id, text, parse_mode, reply_markup, media_file_id, media_type)


async def delete_user_message(message) -> None:
    """Silently delete a user's text input (keeps chat clean in ConversationHandlers)."""
    try:
        await message.delete()
    except Exception:
        pass


def get_menu_msg_id(context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Return the stored persistent menu message ID, or None."""
    return context.user_data.get("menu_msg_id")


# ─── Internal ──────────────────────────────────────────────────────────────────

async def _send_fresh(
    bot: Bot,
    ud: dict,
    chat_id: int,
    text: str,
    parse_mode: str,
    reply_markup,
    media_file_id,
    media_type,
) -> Optional[Message]:
    """Send a brand-new message and update the stored menu_msg_id."""
    try:
        if media_file_id and media_type == "video":
            msg = await bot.send_video(
                chat_id=chat_id,
                video=media_file_id,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        elif media_file_id and media_type == "photo":
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=media_file_id,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        else:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        ud["menu_msg_id"] = msg.message_id
        ud["menu_msg_type"] = media_type if media_file_id else "text"
        return msg
    except Exception as e:
        logger.error(f"_send_fresh: failed to send: {e}")
        return None
