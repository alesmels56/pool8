import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from db.bets import create_bet
from db.users import get_user_language
from bot.keyboards import duration_keyboard, main_keyboard, confirm_keyboard
from bot.ui import update_menu, answer_and_update, delete_user_message
from utils.deeplink import make_bet_link
from utils.i18n import t
from config import BOT_USERNAME

logger = logging.getLogger(__name__)

# ─── Durate disponibili ──────────────────────────────────────────────────────
DURATIONS = {
    "1h":  3600,
    "24h": 86400,
    "3gg": 259200,
}

# ─── Stati del ConversationHandler ───────────────────────────────────────────
(
    ASK_QUESTION,
    ASK_HASHTAG,
    ASK_MEDIA,
    ASK_OPTIONS,
    ASK_MIN_BET,
    ASK_DURATION,
    ASK_PRIVACY,
    CONFIRM_BET,
) = range(8)


# ─── Helper ──────────────────────────────────────────────────────────────────
def _back_kb() -> InlineKeyboardMarkup:
    """Tastiera con solo il pulsante Annulla (torna al menu)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Annulla", callback_data="cancel"),
    ]])


# ─── Step 1: Avvio ───────────────────────────────────────────────────────────
async def start_create_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Avvia la procedura guidata di creazione scommessa."""
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)

    if update.callback_query:
        await update.callback_query.answer()

    context.user_data.clear()
    context.user_data["lang"] = lang
    context.user_data["options"] = []

    await update_menu(
        context, update.effective_chat.id,
        t("prompt_question", lang),
        reply_markup=_back_kb(),
    )
    return ASK_QUESTION


# ─── Step 2: Domanda ─────────────────────────────────────────────────────────
async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve la domanda, cancella il messaggio utente, aggiorna menu."""
    await delete_user_message(update.message)
    lang = context.user_data.get("lang", "it")
    question_text = update.message.text
    if not question_text or not question_text.strip():
        await update_menu(context, update.effective_chat.id,
                          "❌ Inserisci la domanda come testo. Riprova:")
        return ASK_QUESTION
    context.user_data["question"] = question_text.strip()
    await update_menu(context, update.effective_chat.id,
                      t("prompt_hashtags", lang))
    return ASK_HASHTAG


# ─── Step 3: Hashtag ─────────────────────────────────────────────────────────
async def receive_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve gli hashtag, cancella il messaggio utente, chiede il media."""
    await delete_user_message(update.message)
    lang = context.user_data.get("lang", "it")
    tags = re.findall(r'#\w+', update.message.text.strip())
    if not tags:
        await update_menu(context, update.effective_chat.id,
            "❌ <b>Attenzione!</b>\nInserisci almeno un hashtag con #️⃣.\n<i>Es: #sport #twitch</i>",
            reply_markup=_back_kb())
        return ASK_HASHTAG
    context.user_data["hashtags"] = " ".join(tags)
    skip_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Salta (nessun media)", callback_data="media:skip")]])
    await update_menu(context, update.effective_chat.id,
        "📸 <b>Vuoi aggiungere un media alla scommessa?</b>\n\n"
        "Invia una <b>foto</b> o un <b>video</b>, oppure clicca <b>Salta</b>.",
        reply_markup=skip_kb)
    return ASK_MEDIA


# ─── Step 4: Media (opzionale) ───────────────────────────────────────────────
async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve foto/video inviati dall'utente come media della scommessa."""
    message = update.message
    lang = context.user_data.get("lang", "it")

    if message.photo:
        context.user_data["media_file_id"] = message.photo[-1].file_id
        context.user_data["media_type"] = "photo"
        await message.reply_text("✅ Foto ricevuta!")
    elif message.video:
        context.user_data["media_file_id"] = message.video.file_id
        context.user_data["media_type"] = "video"
        await message.reply_text("✅ Video ricevuto!")
    else:
        await message.reply_text(
            "❌ Invia una foto o un video, oppure clicca <b>Salta</b>.",
            parse_mode="HTML",
        )
        return ASK_MEDIA

    return await _ask_options(update, context)


async def skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback: l'utente salta il media."""
    await update.callback_query.answer()
    # No media stored
    return await _ask_options(update, context)


async def _ask_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Helper: chiede le opzioni della scommessa."""
    lang = context.user_data.get("lang", "it")
    options_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Fine (aggiungi opzioni)", callback_data="options_done")
    ]])
    await update.effective_message.reply_text(
        t("prompt_options", lang),
        parse_mode="HTML",
        reply_markup=options_keyboard,
    )
    return ASK_OPTIONS


# ─── Step 5: Opzioni ─────────────────────────────────────────────────────────
async def receive_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve un'opzione, cancella il messaggio utente, aggiorna menu."""
    await delete_user_message(update.message)
    option = update.message.text.strip()
    if not option:
        return ASK_OPTIONS
    options: List[str] = context.user_data.setdefault("options", [])
    if len(options) >= 8:
        await update_menu(context, update.effective_chat.id, "⚠️ Massimo 8 opzioni.", reply_markup=_back_kb())
        return ASK_OPTIONS
    if option in options:
        await update_menu(context, update.effective_chat.id, f"⚠️ '{option}' è già presente.", reply_markup=_back_kb())
        return ASK_OPTIONS
    options.append(option)
    options_list = "\n".join(f"  {i+1}. {o}" for i, o in enumerate(options))
    done_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Fine", callback_data="options_done")]])
    await update_menu(context, update.effective_chat.id,
        f"✅ Opzione aggiunta!\n\n<b>Opzioni attuali:</b>\n{options_list}\n\nAggiungi un'altra, oppure clicca <b>Fine</b>.",
        reply_markup=done_kb)
    return ASK_OPTIONS


async def options_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback Fine opzioni → chiede la puntata minima."""
    query = update.callback_query
    await query.answer()

    options = context.user_data.get("options", [])
    if len(options) < 2:
        await query.edit_message_text(
            "❌ Devi inserire almeno 2 opzioni.\nInserisci le opzioni e poi clicca Fine."
        )
        return ASK_OPTIONS

    lang = context.user_data.get("lang", "it")
    await query.edit_message_text(
        t("prompt_min_bet", lang),
        parse_mode="HTML",
    )
    return ASK_MIN_BET


# ─── Step 6: Puntata minima ───────────────────────────────────────────────────
async def receive_min_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve la puntata minima, cancella il messaggio utente."""
    await delete_user_message(update.message)
    try:
        min_bet = Decimal(update.message.text.strip().replace(",", "."))
        if min_bet <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await update_menu(context, update.effective_chat.id,
                          "❌ Inserisci un numero positivo (es. 5 oppure 2.50):",
                          reply_markup=_back_kb())
        return ASK_MIN_BET
    context.user_data["min_bet"] = str(min_bet)
    lang = context.user_data.get("lang", "it")
    # Aggiungi Annulla alla keyboard della durata
    from telegram import InlineKeyboardMarkup as IKM
    dur_kb = duration_keyboard()
    dur_rows = list(dur_kb.inline_keyboard) + [[InlineKeyboardButton("🏠 Annulla", callback_data="cancel")]]
    await update_menu(context, update.effective_chat.id,
                      t("prompt_duration", lang), reply_markup=InlineKeyboardMarkup(dur_rows))
    return ASK_DURATION


# ─── Step 7: Durata ──────────────────────────────────────────────────────────
async def receive_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve la durata e chiede la privacy."""
    query = update.callback_query
    await query.answer()

    duration_key = query.data.split(":")[1]
    context.user_data["duration_key"] = duration_key
    seconds = DURATIONS[duration_key]
    expires_at = datetime.utcnow() + timedelta(seconds=seconds)
    context.user_data["expires_at"] = expires_at.isoformat()

    lang = context.user_data.get("lang", "it")
    await update_menu(
        context, update.effective_chat.id,
        t("prompt_privacy", lang),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_public", lang), callback_data="privacy:public")],
            [InlineKeyboardButton(t("btn_private", lang), callback_data="privacy:private")],
            [InlineKeyboardButton("🏠 Annulla", callback_data="cancel")],
        ]),
    )
    return ASK_PRIVACY


# ─── Step 8: Privacy ─────────────────────────────────────────────────────────
async def receive_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve la scelta privacy e mostra il riepilogo."""
    query = update.callback_query
    await query.answer()

    is_public = (query.data == "privacy:public")
    context.user_data["is_public"] = is_public

    lang = context.user_data.get("lang", "it")
    question = context.user_data["question"]
    hashtags = context.user_data.get("hashtags", "")
    options = context.user_data["options"]
    min_bet = context.user_data["min_bet"]
    expires_at = datetime.fromisoformat(context.user_data["expires_at"])
    privacy_label = t("btn_public" if is_public else "btn_private", lang)
    has_media = "✅ Sì" if context.user_data.get("media_file_id") else "❌ No"

    options_list = "\n".join(f"  • {o}" for o in options)
    summary = (
        f"📋 <b>Riepilogo Scommessa</b>\n\n"
        f"❓ <b>Domanda:</b> {question}\n"
        f"🏷️ <b>Tag:</b> {hashtags}\n"
        f"📸 <b>Media allegato:</b> {has_media}\n\n"
        f"🔘 <b>Opzioni:</b>\n{options_list}\n\n"
        f"💧 <b>Liquidità Base (Seed):</b> {min_bet} USDT\n"
        f"⏱ <b>Scadenza:</b> {expires_at.strftime('%d/%m/%Y %H:%M')} UTC\n"
        f"🕵️ <b>Visibilità:</b> {privacy_label}\n\n"
        f"Confermi la creazione? Verranno prelevati {min_bet} USDT dal tuo saldo."
    )

    await query.edit_message_text(
        summary,
        parse_mode="HTML",
        reply_markup=confirm_keyboard("bet"),
    )
    return CONFIRM_BET


# ─── Step 9: Conferma ────────────────────────────────────────────────────────
async def confirm_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva la scommessa nel DB e genera il link."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        lang = context.user_data.get("lang", "it")
        await query.edit_message_text(t("err_cancelled", lang))
        context.user_data.clear()
        return ConversationHandler.END

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    min_bet_decimal = Decimal(context.user_data["min_bet"])
    hashtags = context.user_data.get("hashtags", "")

    try:
        bet_uuid = await create_bet(
            pool,
            creator_id=user_id,
            question=context.user_data["question"],
            hashtags=hashtags,
            options=context.user_data["options"],
            min_bet=min_bet_decimal,
            expires_at=datetime.fromisoformat(context.user_data["expires_at"]),
            media_file_id=context.user_data.get("media_file_id"),
            media_type=context.user_data.get("media_type"),
            is_public=context.user_data.get("is_public", True),
        )

        # Liquidità iniziale (Pump Fun seed)
        from db.participations import place_seed_liquidity
        await place_seed_liquidity(
            pool=pool,
            creator_id=user_id,
            bet_uuid=bet_uuid,
            options=context.user_data["options"],
            total_liquidity=min_bet_decimal,
        )
    except Exception as e:
        logger.exception("Errore critico durante la creazione della scommessa")
        lang = context.user_data.get("lang", "it")
        await query.edit_message_text(t("err_generic", lang).format(error=str(e)))
        context.user_data.clear()
        return ConversationHandler.END

    # Successo
    link = make_bet_link(BOT_USERNAME, bet_uuid)
    lang = context.user_data.get("lang", "it")

    share_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            t("btn_share_group", lang),
            url=f"https://t.me/share/url?url={link}&text={t('btn_share', lang)}"
        )
    ]])

    success_text = t("bet_created_success", lang).format(
        amount=min_bet_decimal,
        opt_count=len(context.user_data["options"]),
        link=link,
    )

    await query.edit_message_text(
        success_text,
        parse_mode="HTML",
        reply_markup=share_keyboard,
    )
    context.user_data.clear()
    return ConversationHandler.END
