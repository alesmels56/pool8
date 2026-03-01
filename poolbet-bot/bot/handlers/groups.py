import logging
from uuid import UUID
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from db.bets import get_bet, get_open_bets
from db.users import get_user_language
from utils.formatting import format_bet_message
from config import BOT_USERNAME

logger = logging.getLogger(__name__)

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la ricerca inline: @pool8_bot <testo>."""
    query = update.inline_query.query.strip()
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    
    # Try to get language (default to English if user not registered yet)
    try:
        lang = await get_user_language(pool, user_id)
    except:
        lang = "en"
        
    results = []

    # Se l'utente incolla un UUID specifico
    is_uuid = False
    try:
        UUID(query)
        is_uuid = True
    except ValueError:
        pass

    if is_uuid:
        bet = await get_bet(pool, query)
        if bet and bet["status"] == "open":
            bets = [bet]
        else:
            bets = []
    else:
        # Se vuoto o testo, cerca le ultime pubbliche
        # Per semplicità qui peschiamo le ultime 5. Se query non vuota potremmo filtrare
        # In questo caso facciamo un get_open_bets semplice.
        bets = await get_open_bets(pool, limit=5, offset=0)
        
        if query:
            # Filtro base in memoria (o volendo tramite DB)
            query_lower = query.lower()
            bets = [b for b in bets if query_lower in b["question"].lower() or (b.get("hashtags") and query_lower in b["hashtags"].lower())]

    for bet in bets:
        # Costruisce la preview
        # Limitiamo il title per InlineQueryResult
        title = f"⚽ {bet['question'][:40]}..."
        desc = f"Pool Totale: {bet['pool_total']} USDT"
        
        # Link per aprire il bot su quella bet
        deep_link = f"https://t.me/{BOT_USERNAME}?start=bet_{bet['uuid']}"
        
        # Il contenuto che verrà inviato nella chat di gruppo
        msg_text = (
            f"🔥 <b>{bet['question']}</b>\n\n"
            f"💰 Pool Totale: <b>{bet['pool_total']} USDT</b>\n"
            f"👤 Da: @{bet.get('creator_username', 'Anon')}\n\n"
            f"👇 Clicca qui per scommettere tramite Pool8!"
        )
        
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎰 Scommetti su Pool8", url=deep_link)
        ]])
        
        results.append(
            InlineQueryResultArticle(
                id=str(bet["uuid"]),
                title=title,
                description=desc,
                input_message_content=InputTextMessageContent(msg_text, parse_mode="HTML"),
                reply_markup=reply_markup
            )
        )
        
    if not results:
        results.append(
            InlineQueryResultArticle(
                id="no_results",
                title="Scommesse non trovate",
                description="Prova a creare o cercare una scommessa.",
                input_message_content=InputTextMessageContent(
                    "Crea la tua scommessa su Pool8!", 
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Apri Pool8", url=f"https://t.me/{BOT_USERNAME}")
                ]])
            )
        )

    await update.inline_query.answer(results, cache_time=10, is_personal=True)
