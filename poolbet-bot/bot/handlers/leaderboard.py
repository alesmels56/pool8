"""
bot/handlers/leaderboard.py — Leaderboard: Top Winners and Top Creators.
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.ui import update_menu
from db.users import get_user_language
from utils.i18n import t

logger = logging.getLogger(__name__)


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the weekly leaderboard of top winners and creators."""
    if update.callback_query:
        await update.callback_query.answer()

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)

    # Top 5 Winners (by payout received in last 7 days)
    top_winners = await pool.fetch("""
        SELECT u.username, u.user_id, COALESCE(SUM(t.amount), 0) AS total_won
        FROM transactions t
        JOIN users u ON t.user_id = u.user_id
        WHERE t.type = 'payout' AND t.created_at > NOW() - INTERVAL '7 days'
        GROUP BY u.user_id, u.username
        ORDER BY total_won DESC
        LIMIT 5
    """)

    # Top 5 Creators (by trust score)
    top_creators = await pool.fetch("""
        SELECT username, user_id, trust_score, total_bets_closed
        FROM users
        WHERE total_bets_created > 0
        ORDER BY trust_score DESC, total_bets_closed DESC
        LIMIT 5
    """)

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    lines = [t("leaderboard_title", lang)]

    # Winners
    lines.append(t("leaderboard_winners", lang))
    if top_winners:
        for i, r in enumerate(top_winners):
            name = f"@{r['username']}" if r["username"] else f"User #{r['user_id']}"
            lines.append(f"{medals[i]} {name} — <b>+{float(r['total_won']):.2f} USDT</b>")
    else:
        lines.append(t("leaderboard_no_winners", lang))

    # Creators
    lines.append(t("leaderboard_creators", lang))
    if top_creators:
        for i, r in enumerate(top_creators):
            name = f"@{r['username']}" if r["username"] else f"User #{r['user_id']}"
            lines.append(f"{medals[i]} {name} — <b>{r['trust_score']}%</b> ({r['total_bets_closed']} bets)")
    else:
        lines.append(t("leaderboard_no_creators", lang))

    lines.append(t("leaderboard_footer", lang))

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main"),
    ]])

    await update_menu(
        context, update.effective_chat.id,
        "\n".join(lines),
        reply_markup=keyboard,
    )
