"""
utils/i18n.py — Sistema di traduzione per il Pool8 Bot.
Permette di supportare più lingue (IT, EN) dinamicamente per ogni utente.
"""
from typing import Dict

# Dizionario master delle traduzioni
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "it": {
        # Comandi e Menu
        "menu_balance": "💰 Il mio Saldo",
        "menu_create": "➕ Crea Scommessa",
        "menu_explore": "🌐 Esplora",
        "menu_minigames": "🕹️ Minigiochi",
        "menu_leaderboard": "🏆 Classifiche",
        "btn_challenge": "⚖️ Contesta Risultato",
        "challenge_started": "⚖️ **Scommessa Contestata!**\n\nUn arbitro verificherà il risultato entro 24h. Se il creator ha mentito, verrai premiato.",
        "payout_review": "⏳ **Periodo di Revisione**\n\nIl risultato è stato dichiarato. Gli utenti hanno 24 ore per contestare prima della distribuzione automatica.",
        "err_challenge_self": "❌ Non puoi contestare la tua stessa scommessa.",
        "err_challenge_funds": "❌ Saldo insufficiente per contestare (richiesti {amount} USDT).",
        "resolution_notification": "🔔 <b>Risultato Dichiarato!</b>\n\nScommessa: <i>{question}</i>\nEsito dichiarato dal creator: <b>{winner}</b>\n\nHai {hours} ore per contestare se ritieni che il risultato sia falso. Contestare richiede uno stake di {stake} USDT che perderai se la protesta è infondata.",
        "btn_game_8ball": "🎱 Ball 8 (1-8)",
        "btn_game_mines": "💣 Mines",
        "btn_game_coinflip": "🪙 Testa o Croce",
        "btn_game_dice": "🎲 Dadi",
        "game_8ball_title": "🎱 **Biliardo Ball 8 (1-8)**",
        "game_8ball_title": "🎱 **Biliardo Ball 8 (1-8)**",
        "game_8ball_descr": "Punta su un numero tra 1 e 8. Se la pallina si ferma sul tuo numero, vinci **7x** la tua puntata!\nLe perdite vanno a supporto della piattaforma.",
        "game_8ball_bet": "💰 Puntata: <b>{amount} USDT</b>",
        "game_8ball_target": "🎯 Numero scelto: <b>{target}</b>",
        "game_8ball_win": "🎉 <b>HAI VINTO!</b>\nÈ uscito il numero {num}.\nHai vinto {win_amount} USDT!",
        "game_8ball_loss": "❌ <b>HAI PERSO</b>\nÈ uscito il numero {num}.\nLa tua puntata di {bet_amount} USDT è andata alla piattaforma.",
        "game_8ball_insufficient": "❌ Saldo insufficiente!",
        "btn_play": "🎰 GIOCA!",
        "menu_mybets": "📋 Le mie Bet",
        "menu_help": "ℹ️ Aiuto / Info",
        
        # Creazione Scommessa
        "prompt_question": "🎯 <b>Crea Scommessa</b> — Passo 1/8\n\nInserisci la <b>domanda</b> della scommessa.",
        "prompt_hashtags": "🏷️ <b>Aggiungi Hashtag</b> — Passo 2/8\n\nCategorizza la tua scommessa con uno o più hashtag (es. #calcio).\n<b>Obbligatorio</b> per renderla trovabile nella ricerca.",
        "prompt_options": "📝 <b>Aggiungi Opzioni</b> — Passo 4/8\n\nInserisci le opzioni una alla volta (min 2, max 8).",
        "prompt_min_bet": "💧 <b>Liquidità Iniziale</b> — Passo 5/8\n\nQuanti USDT vuoi mettere come pool base?\n<i>L'importo sarà diviso equamente tra le opzioni.</i>",
        "prompt_duration": "⏱ <b>Durata</b> — Passo 6/8\n\nQuanto deve durare la scommessa?",
        "prompt_privacy": "🕵️ <b>Visibilità</b> — Passo 7/8\n\nVuoi che la scommessa sia visibile nel feed <b>Esplora</b> o solo tramite link diretto?",
        "btn_public": "🌐 Pubblica (Feed Esplora)",
        "btn_private": "🔒 Privata (solo Link)",
        "bet_created_success": "✅ <b>Scommessa creata!</b>\n💧 Hai versato {amount} USDT sulle {opt_count} opzioni.\n\n🔗 Link diretto:\n<code>{link}</code>\n\nCondividi il link — chi lo apre può partecipare istantaneamente!",
        "btn_share_group": "📢 Condividi nel Gruppo",
        "btn_share": "🔗 Condividi questa Scommessa",
        "btn_search_tag": "🔍 Cerca per Tag",
        "btn_reset_search": "🌐 Chiudi Ricerca",
        "search_prompt": "🔍 <b>Motore di Ricerca</b>\n\nScrivi l'hashtag da cercare (es. #calcio) o invia 'annulla'.",
        # Saldo e Wallet
        "btn_withdraw": "💸 Preleva",
        "btn_history": "📊 Storico",
        "btn_copy_addr": "📋 Copia Indirizzo",
        "btn_qr": "📷 Mostra QR",
        "btn_deposit_info": "➕ Ricarica (info)",
        "btn_daily": "🎁 Faucet Giornaliero",
        "daily_success": "🎁 <b>FAUCET RISCOSSO!</b>\n\nHai ottenuto <b>{bonus} USDT</b> in crediti bonus.\n🔥 Streak attuale: <b>{streak} giorni</b>\n⭐ XP Guadagnati: <b>+{xp} XP</b>\n\n<i>Torna domani per aumentare il moltiplicatore!</i>",
        "daily_already": "⏳ Hai già riscosso il faucet di oggi.\n\n<i>Il faucet si resetta a mezzanotte (UTC).</i>",
        "btn_referral": "👥 Porta un Amico",
        "referral_text": (
            "👥 <b>Programma Referral</b>\n\n"
            "Invita i tuoi amici e ricevi un bonus per ogni nuovo utente che si iscrive!\n\n"
            "Ecco il tuo link unico:\n<code>{link}</code>"
        ),
        "trust_score": "🛡️ Affidabilità: <b>{score}%</b>",
        
        # Scommessa e Partecipazione
        "btn_share": "🔗 Condividi questa Scommessa",
        "btn_cancel": "❌ Annulla",
        "btn_confirm": "✅ Conferma",
        "btn_custom_amount": "✏️ Inserisci importo personalizzato",
        "btn_close_bet": "🔒 Chiudi Scommessa",
        "btn_back_menu": "🔙 Torna al Menu",
        
        # Mance / Tipping
        "btn_tip": "💸 Invia Mancia",
        "tip_ask_username": "💸 <b>Invia una Mancia</b>\n\nA chi vuoi inviare i fondi? Inserisci il suo @username Telegram:",
        "tip_ask_amount": "💸 <b>Invia mancia a @{username}</b>\n\nQuanto vuoi inviare in USDT?\n<i>(Verrà trattenuta una fee del 5% per la piattaforma)</i>",
        "tip_success": "✅ <b>Mancia Inviata!</b>\nHai inviato {amount} USDT a @{username}.",
        "tip_received": "💸 <b>Mancia Ricevuta!</b>\nHai appena ricevuto <b>{amount} USDT</b> da @{sender}.",
        "err_user_not_found": "❌ Utente non trovato. Assicurati che esista e abbia avviato il bot.",
        "err_self_tip": "❌ Non puoi inviare una mancia a te stesso!",
        
        # Lingue
        "lang_updated": "✅ Lingua aggiornata in Italiano!",
        "lang_prompt": "🌍 Seleziona la tua lingua:",
        
        "welcome_text": (
            "👋 <b>Benvenuto su Pool8 Bot!</b>\n\n"
            "Crea le tue scommesse pubbliche o private, invita i tuoi amici e gestisci il tuo pool direttamente su Telegram.\n\n"
            "👇 <b>Usa i bottoni qui sotto per iniziare</b> 👇"
        ),
        "welcome_ticker": "🔥 <b>Record Vincite:</b> {ticker}\n\n",
        # Classifiche
        "leaderboard_title": "🏆 <b>CLASSIFICHE POOL8</b>\n━━━━━━━━━━━━━━━━━━━━",
        "leaderboard_winners": "\n🥇 <b>Top Vincitori (ultimi 7 giorni)</b>",
        "leaderboard_creators": "\n🛡️ <b>Top Creatori (per Affidabilità)</b>",
        "leaderboard_no_winners": "   Ancora nessuna vincita questa settimana.",
        "leaderboard_no_creators": "   Ancora nessun creatore in classifica.",
        "leaderboard_footer": "\n━━━━━━━━━━━━━━━━━━━━\n🔄 Aggiornata ogni settimana. Crea e chiudi scommesse per salire!",
        "btn_public": "🌐 Pubblica (nel Feed)",
        "btn_private": "🔒 Privata (solo Link)",
        "prompt_privacy": "🕵️ <b>Visibilità Scommessa</b>\n\nVuoi che la tua scommessa sia visibile a tutti nella sezione <b>Esplora</b> o vuoi che sia accessibile solo tramite link diretto?",
        "bet_not_found": "❌ Scommessa non trovata o scaduta.",
        "deposit_tutorial": (
            "💳 <b>TUTORIAL RICARICA - COME DEPOSITARE</b>\n\n"
            "Per scommettere su PoolBet hai bisogno di <b>USDT (Tether)</b> sulla rete <b>Polygon (MATIC)</b>.\nSegui questi passaggi:\n\n"
            "<b>1️⃣ PROCURATI UN WALLET O UN EXCHANGE</b>\n"
            "Se non hai criptovalute, scarica un'app come <b>Binance, Bybit, Coinbase o Crypto.com</b>. Registrati e compra USDT usando Euro (carta/bonifico).\n\n"
            "<b>2️⃣ VAI SUL PRELIEVO (WITHDRAW)</b>\n"
            "Dal tuo exchange, clicca su: -> 'USDT' -> 'Preleva / Withdraw' -> 'Invia tramite Rete Crypto'.\n\n"
            "<b>3️⃣ IMPOSTA I DATI DI INVIO</b>\n"
            "▪️ <b>Indirizzo Destinazione:</b> Clicca qui sotto per copiarlo:\n"
            "<code>{address}</code>\n"
            "▪️ <b>Rete (Network):</b> <tg-spoiler>POLYGON (MATIC)</tg-spoiler> ⚠️ <i>[FONDAMENTALE: Scegli tassativamente Polygon, se scegli ERC20 o Tron perdi i fondi!]</i>\n"
            "▪️ <b>Importo:</b> La cifra che desideri.\n\n"
            "<b>4️⃣ CONFERMA</b>\n"
            "Conferma il prelievo. La rete Polygon impiega in media 1-3 minuti.\n\n"
            "<b>✅ CREDITO AUTOMATICO</b>\n"
            "Non devi fare altro. Riceverai un messaggio qui sul bot non appena i fondi arrivano!\n\n"
            "🎁 <b>PROMOZIONE</b>: Ogni deposito ≥ <b>50 USDT</b> riceve in automatico un <b>Bonus del +5%</b>!"
        ),
        "err_profile": "❌ Profilo non trovato. Usa /start per registrarti.",
        "err_insufficient": "❌ Saldo insufficiente.",
        "err_bet_not_found": "❌ Scommessa non trovata.",
        "err_invalid_option": "❌ Opzione non valida.",
        "err_cancelled": "❌ Operazione annullata.",
        "err_generic": "❌ Errore: {error}",
    },
    "en": {
        # Comandi e Menu
        "menu_balance": "💰 My Balance",
        "menu_create": "➕ Create Bet",
        "menu_explore": "🌐 Explore",
        "menu_minigames": "🕹️ Mini-games",
        "menu_leaderboard": "🏆 Leaderboards",
        "btn_challenge": "⚖️ Dispute Result",
        "challenge_started": "⚖️ **Bet Disputed!**\n\nAn admin will verify the result within 24h. If the creator lied, you will be rewarded.",
        "payout_review": "⏳ **Review Period**\n\nThe result has been declared. Users have 24 hours to dispute before the automatic payout.",
        "err_challenge_self": "❌ You cannot dispute your own bet.",
        "err_challenge_funds": "❌ Insufficient balance to dispute ({amount} USDT required).",
        "btn_game_8ball": "🎱 Ball 8 (1-8)",
        "btn_game_mines": "💣 Mines (Mine)",
        "btn_game_coinflip": "🪙 Coin Flip",
        "btn_game_dice": "🎲 Dice",
        "game_8ball_title": "🎱 **Pool Ball 8 (1-8)**",
        "game_8ball_title": "🎱 **Pool Ball 8 (1-8)**",
        "game_8ball_descr": "Bet on a number between 1 and 8. If the ball stops on your number, you win **7x** your bet!\nLosses go to support the platform.",
        "game_8ball_bet": "💰 Bet: <b>{amount} USDT</b>",
        "game_8ball_target": "🎯 Target Number: <b>{target}</b>",
        "game_8ball_win": "🎉 <b>YOU WON!</b>\nNumber {num} came out.\nYou won {win_amount} USDT!",
        "game_8ball_loss": "❌ <b>YOU LOST</b>\nNumber {num} came out.\nYour bet of {bet_amount} USDT went to the platform.",
        "game_8ball_insufficient": "❌ Insufficient balance!",
        "btn_play": "🎰 PLAY!",
        "menu_mybets": "📋 My Bets",
        "menu_help": "ℹ️ Help / Info",

        # Bet Creation
        "prompt_question": "🎯 <b>Create Bet</b> — Step 1/8\n\nEnter the <b>question</b> for the bet.",
        "prompt_hashtags": "🏷️ <b>Add Hashtags</b> — Step 2/8\n\nCategorize your bet with one or more hashtags (e.g. #sports).\n<b>Mandatory</b> to make it searchable.",
        "prompt_options": "📝 <b>Add Options</b> — Step 4/8\n\nEnter options one by one (min 2, max 8).",
        "prompt_min_bet": "💧 <b>Initial Liquidity</b> — Step 5/8\n\nHow many USDT do you want as the base pool?\n<i>This amount will be split equally among options.</i>",
        "prompt_duration": "⏱ <b>Duration</b> — Step 6/8\n\nHow long should the bet last?",
        "prompt_privacy": "🕵️ <b>Visibility</b> — Step 7/8\n\nShould your bet appear in the <b>Explore</b> feed or be link-only?",
        "btn_public": "🌐 Public (Explore Feed)",
        "btn_private": "🔒 Private (Link only)",
        "bet_created_success": "✅ <b>Bet Created!</b>\n💧 You provided {amount} USDT split among {opt_count} options.\n\n🔗 Direct Link:\n<code>{link}</code>\n\nShare this link — anyone who opens it can participate instantly!",
        "btn_share_group": "📢 Share in Group",
        "btn_share": "🔗 Share this Bet",
        "btn_search_tag": "🔍 Search by Tag",
        "btn_reset_search": "🌐 Reset Search",
        "search_prompt": "🔍 <b>Search Engine</b>\n\nWrite the hashtag to search for (e.g. #sports) or send 'cancel'.",
        # Leaderboard
        "leaderboard_title": "🏆 <b>POOL8 LEADERBOARD</b>\n━━━━━━━━━━━━━━━━━━━━",
        "leaderboard_winners": "\n🥇 <b>Top Winners (last 7 days)</b>",
        "leaderboard_creators": "\n🛡️ <b>Top Creators (by Trust Score)</b>",
        "leaderboard_no_winners": "   No wins yet this week.",
        "leaderboard_no_creators": "   No creators on the leaderboard yet.",
        "leaderboard_footer": "\n━━━━━━━━━━━━━━━━━━━━\n🔄 Updated weekly. Create and close bets to climb!",
        # Saldo e Wallet
        "btn_withdraw": "💸 Withdraw",
        "btn_history": "📊 History",
        "btn_copy_addr": "📋 Copy Address",
        "btn_qr": "📷 Show QR",
        "btn_deposit_info": "➕ Deposit (info)",
        "btn_daily": "🎁 Daily Faucet",
        "daily_success": "🎁 <b>FAUCET CLAIMED!</b>\n\nYou received <b>{bonus} USDT</b> in bonus credits.\n🔥 Current streak: <b>{streak} days</b>\n⭐ XP Earned: <b>+{xp} XP</b>\n\n<i>Come back tomorrow to increase your multiplier!</i>",
        "daily_already": "⏳ You have already claimed today's faucet.\n\n<i>The faucet resets at midnight (UTC).</i>",
        
        # Scommessa e Partecipazione
        "btn_share": "🔗 Share this Bet",
        "btn_cancel": "❌ Cancel",
        "btn_confirm": "✅ Confirm",
        "btn_custom_amount": "✏️ Enter custom amount",
        "btn_close_bet": "🔒 Close Bet",
        "btn_back_menu": "🔙 Back to Menu",

        # Mance / Tipping
        "btn_tip": "💸 Send Tip",
        "tip_ask_username": "💸 <b>Send a Tip</b>\n\nWho do you want to tip? Enter their Telegram @username:",
        "tip_ask_amount": "💸 <b>Send tip to @{username}</b>\n\nHow many USDT do you want to send?\n<i>(A 5% platform fee will be applied)</i>",
        "tip_success": "✅ <b>Tip Sent!</b>\nYou have sent {amount} USDT to @{username}.",
        "tip_received": "💸 <b>Tip Received!</b>\nYou just received <b>{amount} USDT</b> from @{sender}.",
        "err_user_not_found": "❌ User not found. Make sure they exist and have started the bot.",
        "err_self_tip": "❌ You can't send a tip to yourself!",
        "resolution_notification": "🔔 <b>Result Declared!</b>\n\nBet: <i>{question}</i>\nDeclared outcome by creator: <b>{winner}</b>\n\nYou have {hours} hours to contest if you believe the result is false. Challenging requires a stake of {stake} USDT which you will lose if the protest is groundless.",
        
        # Lingue
        "lang_updated": "✅ Language updated to English!",
        "lang_prompt": "🌍 Select your language:",
        
        "welcome_text": (
            "👋 <b>Welcome to Pool8 Bot!</b>\n\n"
            "Create your public or private bets, invite your friends and manage your pool directly on Telegram.\n\n"
            "👇 <b>Use the buttons below to start</b> 👇"
        ),
        "welcome_ticker": "🔥 <b>Latest Big Wins:</b> {ticker}\n\n",
        "btn_referral": "👥 Invite Friends",
        "referral_text": (
            "👥 <b>Referral Program</b>\n\n"
            "Invite your friends and earn a bonus for every new user who signs up!\n\n"
            "Here is your unique link:\n<code>{link}</code>"
        ),
        "trust_score": "🛡️ Trust Score: <b>{score}%</b>",
        "btn_public": "🌐 Public (in Feed)",
        "btn_private": "🔒 Private (Link only)",
        "prompt_privacy": "🕵️ <b>Bet Visibility</b>\n\nDo you want your bet to be visible to everyone in the <b>Explore</b> section, or link-only?",
        "bet_not_found": "❌ Bet not found or expired.",
        "deposit_tutorial": (
            "💳 <b>DEPOSIT TUTORIAL - HOW TO FUND</b>\n\n"
            "To bet on PoolBet, you need <b>USDT (Tether)</b> on the <b>Polygon (MATIC)</b> network.\nFollow these steps:\n\n"
            "<b>1️⃣ GET A WALLET OR EXCHANGE</b>\n"
            "If you don't have crypto, download an app like <b>Binance, Bybit, Coinbase, or Crypto.com</b>. Register and buy USDT using fiat (card/bank).\n\n"
            "<b>2️⃣ GO TO WITHDRAWAL</b>\n"
            "From your exchange, click: -> 'USDT' -> 'Withdraw' -> 'Send via Crypto Network'.\n\n"
            "<b>3️⃣ SET SENDING DETAILS</b>\n"
            "▪️ <b>Destination Address:</b> Click below to copy it:\n"
            "<code>{address}</code>\n"
            "▪️ <b>Network:</b> <tg-spoiler>POLYGON (MATIC)</tg-spoiler> ⚠️ <i>[CRUCIAL: You must select Polygon, choosing ERC20 or Tron will result in lost funds!]</i>\n"
            "▪️ <b>Amount:</b> The amount you wish to deposit.\n\n"
            "<b>4️⃣ CONFIRM</b>\n"
            "Confirm the withdrawal. The Polygon network takes 1-3 minutes on average.\n\n"
            "<b>✅ AUTOMATIC CREDIT</b>\n"
            "You don't need to do anything else. You'll receive a message here on the bot once the funds arrive!\n\n"
            "🎁 <b>PROMOTION</b>: Every deposit ≥ <b>50 USDT</b> automatically receives a <b>+5% Bonus</b>!"
        ),
        "err_profile": "❌ Profile not found. Use /start to register.",
        "err_insufficient": "❌ Insufficient balance.",
        "err_bet_not_found": "❌ Bet not found.",
        "err_invalid_option": "❌ Invalid option.",
        "err_cancelled": "❌ Operation cancelled.",
        "err_generic": "❌ Error: {error}",
    },
    "fr": {
        # Comandi e Menu
        "menu_balance": "💰 Mon Solde",
        "menu_create": "➕ Créer un Pari",
        "menu_explore": "🌐 Explorer",
        "menu_minigames": "🕹️ Mini-jeux",
        "menu_leaderboard": "🏆 Classements",
        "btn_game_mines": "💣 Mines (Mine)",
        "btn_game_coinflip": "🪙 Pile ou Face",
        "btn_game_dice": "🎲 Dés",
        "menu_mybets": "📋 Mes Paris",
        "menu_help": "ℹ️ Aide / Info",
        
        # Création de Pari
        "prompt_question": "Étape 1/4 — Entrez la <b>question</b> del pari.",
        "prompt_hashtags": "🏷️ <b>Ajouter des Hashtags</b>\n\nÉcrivez un ou plusieurs hashtags (ex. #sport).",
        "prompt_options": "📝 Étape 2/4 — Entrez les <b>options</b>.",
        "btn_search_tag": "🔍 Rechercher par Tag",
        "btn_reset_search": "🌐 Réinitialiser la Recherche",
        "search_prompt": "🔍 <b>Moteur de Recherche</b>\n\nÉcrivez le hashtag à rechercher (ex. #sport) ou envoyez 'annulla'.",
        # Saldo e Wallet
        "btn_withdraw": "💸 Retirer",
        "btn_history": "📊 Historique",
        "btn_copy_addr": "📋 Copier l'Adresse",
        "btn_qr": "📷 Afficher le QR",
        "btn_deposit_info": "➕ Dépôt (info)",
        
        # Scommessa e Partecipazione
        "btn_share": "🔗 Partager ce Pari",
        "btn_cancel": "❌ Annuler",
        "btn_confirm": "✅ Confirmer",
        "btn_custom_amount": "✏️ Entrer un montant personnalisé",
        "btn_close_bet": "🔒 Fermer le Pari",
        "btn_back_menu": "🔙 Retour au Menu",
        
        # Lingue
        "lang_updated": "✅ Langue mise à jour en Français!",
        "lang_prompt": "🌍 Sélectionnez votre langue:",
        
        # Start & Welcome
        "welcome_text": (
            "👋 <b>Bienvenue sur Pool8 Bot!</b>\n\n"
            "Le moyen le plus simple de parier avec vos amis en utilisant <b>USDT sur Polygon</b>.\n\n"
            "💡 <b>Comment ça marche:</b>\n"
            "1️⃣ <b>Dépôt</b> — Rechargez en USDT une seule fois sur votre portefeuille dédié.\n"
            "2️⃣ <b>Créer</b> — Démarrez un nouveau pari et partagez-le n'importe où.\n"
            "3️⃣ <b>Participer</b> — Pariez sur des cagnottes actives en un seul clic.\n"
            "4️⃣ <b>Gagner</b> — Les prix sont crédités instantanément!\n\n"
            "💳 <b>Système de Crédits</b>\n"
            "Faites <u>un seul dépôt</u> et utilisez vos crédits pour autant de paris que vous le souhaitez, sans frais de gaz. Retirez quand vous le souhaitez.\n\n"
            "👇 <b>Utilisez les boutons ci-dessous pour commencer</b> 👇"
        ),
        "bet_not_found": "❌ Pari introuvable ou expiré.",
        "deposit_tutorial": (
            "💳 <b>TUTORIEL DE RECHARGE - COMMENT DÉPOSER</b>\n\n"
            "Pour parier sur PoolBet, vous avez besoin de <b>USDT (Tether)</b> envoyés via le réseau <b>Polygon (MATIC)</b>.\nSuivez ces étapes simples:\n\n"
            "<b>1️⃣ OBTENIR UN PORTEFEUILLE OU ÉCHANGE</b>\n"
            "Si vous n'avez pas de crypto, téléchargez une application comme <b>Binance, Bybit, Coinbase ou Crypto.com</b>. Inscrivez-vous, vérifiez votre identité et achetez des USDT en Fiat (Carte/Virement).\n\n"
            "<b>2️⃣ ALLER AU RETRAIT</b>\n"
            "Depuis votre échange, cliquez sur : -> 'USDT' -> 'Retirer' -> 'Envoyer via réseau Crypto'.\n\n"
            "<b>3️⃣ DÉFINIR LES DÉTAILS</b>\n"
            "▪️ <b>Adresse de destination :</b> Cliquez ci-dessous pour copier :\n"
            "<code>{address}</code>\n"
            "▪️ <b>Réseau :</b> <tg-spoiler>POLYGON (MATIC)</tg-spoiler> ⚠️ <i>[CRITIQUE : Choisissez Polygon, si vous choisissez ERC20 ou Tron, vous perdrez vos fonds!]</i>\n"
            "▪️ <b>Montant :</b> Le montant à recharger.\n\n"
            "<b>4️⃣ CONFIRMER</b>\n"
            "Confirmez le transfert. Le réseau Polygon prend en moyenne 1 à 3 minutes pour se terminer.\n\n"
            "<b>✅ SOLDE CRÉDITÉ AUTOMATIQUEMENT</b>\n"
            "Vous n'avez rien d'autre à faire. Vous recevrez un message ici lorsque les fonds arriveront!\n\n"
            "🎁 <b>PROMO</b> : Chaque dépôt ≥ <b>50 USDT</b> reçoit automatiquement <b>+5% de bonus</b>!"
        ),
    },
    "de": {
        # Comandi e Menu
        "menu_balance": "💰 Mein Guthaben",
        "menu_create": "➕ Wette erstellen",
        "menu_explore": "🌐 Entdecken",
        "menu_minigames": "🕹️ Minispiele",
        "menu_leaderboard": "🏆 Bestenlisten",
        "btn_game_mines": "💣 Mines (Mine)",
        "btn_game_coinflip": "🪙 Kopf oder Zahl",
        "btn_game_dice": "🎲 Würfel",
        "menu_mybets": "📋 Meine Wetten",
        "menu_help": "ℹ️ Hilfe / Info",
        
        # Wette Erstellen
        "prompt_question": "Schritt 1/4 — Geben Sie die <b>Frage</b> ein.",
        "prompt_hashtags": "🏷️ <b>Hashtags hinzufügen</b>\n\nSchreiben Sie einen oder mehrere Hashtags (z.B. #fussball).",
        "prompt_options": "📝 Schritt 2/4 — Geben Sie <b>Optionen</b> ein.",
        "btn_search_tag": "🔍 Suche nach Tag",
        "btn_reset_search": "🌐 Suche zurücksetzen",
        "search_prompt": "🔍 <b>Suchmaschine</b>\n\nGeben Sie den zu suchenden Hashtag ein (z.B. #sport) oder senden Sie 'annulla'.",
        # Saldo e Wallet
        "btn_withdraw": "💸 Abheben",
        "btn_history": "📊 Verlauf",
        "btn_copy_addr": "📋 Adresse kopieren",
        "btn_qr": "📷 QR anzeigen",
        "btn_deposit_info": "➕ Einzahlung (Info)",
        
        # Scommessa e Partecipazione
        "btn_share": "🔗 Diese Wette teilen",
        "btn_cancel": "❌ Abbrechen",
        "btn_confirm": "✅ Bestätigen",
        "btn_custom_amount": "✏️ Benutzerdefinierten Betrag eingeben",
        "btn_close_bet": "🔒 Wette schließen",
        "btn_back_menu": "🔙 Zurück zum Menü",
        
        # Lingue
        "lang_updated": "✅ Sprache aktualisiert auf Deutsch!",
        "lang_prompt": "🌍 Wählen Sie Ihre Sprache:",
        
        # Start & Welcome
        "welcome_text": (
            "👋 <b>Willkommen beim Pool8 Bot!</b>\n\n"
            "Der einfachste Weg, mit Ihren Freunden zu wetten, indem Sie <b>USDT auf Polygon</b> verwenden.\n\n"
            "💡 <b>Wie es funktioniert:</b>\n"
            "1️⃣ <b>Einzahlen</b> — Laden Sie einmalig USDT auf Ihre dedizierte Wallet auf.\n"
            "2️⃣ <b>Erstellen</b> — Starten Sie eine neue Wette und teilen Sie sie überall.\n"
            "3️⃣ <b>Teilnehmen</b> — Wetten Sie mit nur einem Tipp auf aktive Pools.\n"
            "4️⃣ <b>Gewinnen</b> — Preise werden sofort gutgeschrieben!\n\n"
            "💳 <b>Kredit-System</b>\n"
            "Machen Sie <u>eine einzige Einzahlung</u> und verwenden Sie Ihre Credits für so viele Wetten, wie Sie möchten, ohne Gasgebühren. Vorbehaltlos abheben, wann immer Sie wollen.\n\n"
            "👇 <b>Verwenden Sie die Schaltflächen unten, um zu beginnen</b> 👇"
        ),
        "bet_not_found": "❌ Wette nicht gefunden oder abgelaufen.",
        "deposit_tutorial": (
            "💳 <b>AUFLADE-TUTORIAL - WIE MAN EINZAHLT</b>\n\n"
            "Um bei PoolBet zu wetten, benötigen Sie <b>USDT (Tether)</b> über das <b>Polygon (MATIC)</b>-Netzwerk.\nBefolgen Sie diese Schritte:\n\n"
            "<b>1️⃣ WALLET ODER BÖRSE HOLEN</b>\n"
            "Wenn Sie keine Krypto haben, laden Sie eine App wie <b>Binance, Bybit, Coinbase oder Crypto.com</b> herunter. Registrieren Sie sich und kaufen Sie USDT mit Fiat (Karte/Überweisung).\n\n"
            "<b>2️⃣ ZUR AUSZAHLUNG GEHEN</b>\n"
            "Klicken Sie in Ihrer Börse auf: -> 'USDT' -> 'Auszahlen' -> 'Über Krypto-Netzwerk senden'.\n\n"
            "<b>3️⃣ SEND DETAILS FESTLEGEN</b>\n"
            "▪️ <b>Zieladresse:</b> Klicken Sie unten zum Kopieren:\n"
            "<code>{address}</code>\n"
            "▪️ <b>Netzwerk:</b> <tg-spoiler>POLYGON (MATIC)</tg-spoiler> ⚠️ <i>[WICHTIG: Wählen Sie unbedingt Polygon, wenn Sie ERC20 oder Tron wählen, verlieren Sie Ihr Geld!]</i>\n"
            "▪️ <b>Betrag:</b> Der gewünschte Betrag.\n\n"
            "<b>4️⃣ BESTÄTIGEN</b>\n"
            "Bestätigen Sie die Überweisung. Das Polygon-Netzwerk benötigt im Durchschnitt 1-3 Minuten.\n\n"
            "<b>✅ GUTHABEN AUTOMATISCH GUTGESCHRIEBEN</b>\n"
            "Sie müssen nichts weiter tun. Sie erhalten hier eine Nachricht, wenn das Geld ankommt!\n\n"
            "🎁 <b>PROMO</b>: Jede Einzahlung ≥ <b>50 USDT</b> erhält automatisch einen <b>+5% Bonus</b>!"
        ),
        "err_profile": "❌ Profil nicht gefunden. Starten Sie mit /start.",
        "err_insufficient": "❌ Unzureichendes Guthaben.",
        "err_bet_not_found": "❌ Wette nicht gefunden.",
        "err_invalid_option": "❌ Ungültige Option.",
        "err_cancelled": "❌ Vorgang abgebrochen.",
        "err_generic": "❌ Fehler: {error}",
    },
    "es": {
        # Comandi e Menu
        "menu_balance": "💰 Mi Saldo",
        "menu_create": "➕ Crear Apuesta",
        "menu_explore": "🌐 Explorar",
        "menu_minigames": "🕹️ Minijuegos",
        "menu_leaderboard": "🏆 Clasificaciones",
        "btn_game_mines": "💣 Mines (Mine)",
        "btn_game_coinflip": "🪙 Cara o Cruz",
        "btn_game_dice": "🎲 Dados",
        "menu_mybets": "📋 Mis Apuestas",
        "menu_help": "ℹ️ Ayuda / Info",
        
        # Creación de Apuesta
        "prompt_question": "Paso 1/4 — Ingrese la <b>pregunta</b>.",
        "prompt_hashtags": "🏷️ <b>Añadir Hashtags</b>\n\nEscriba uno o más hashtags (ej. #futbol).",
        "prompt_options": "📝 Paso 2/4 — Ingrese <b>opciones</b>.",
        "btn_search_tag": "🔍 Buscar por Tag",
        "btn_reset_search": "🌐 Reiniciar Búsqueda",
        "search_prompt": "🔍 <b>Motor de Búsqueda</b>\n\nEscriba el hashtag a buscar (ej. #deportes) o envíe 'annulla'.",
        # Saldo e Wallet
        "btn_withdraw": "💸 Retirar",
        "btn_history": "📊 Historial",
        "btn_copy_addr": "📋 Copiar Dirección",
        "btn_qr": "📷 Mostrar QR",
        "btn_deposit_info": "➕ Depósito (info)",
        
        # Scommessa e Partecipazione
        "btn_share": "🔗 Compartir esta Apuesta",
        "btn_cancel": "❌ Cancelar",
        "btn_confirm": "✅ Confirmar",
        "btn_custom_amount": "✏️ Ingresar cantidad personalizada",
        "btn_close_bet": "🔒 Cerrar Apuesta",
        "btn_back_menu": "🔙 Volver al Menú",
        
        # Lingue
        "lang_updated": "✅ ¡Idioma actualizado a Español!",
        "lang_prompt": "🌍 Selecciona tu idioma:",
        
        # Start & Welcome
        "welcome_text": (
            "👋 <b>¡Bienvenido a Pool8 Bot!</b>\n\n"
            "La forma más fácil de apostar con tus amigos usando <b>USDT en Polygon</b>.\n\n"
            "💡 <b>Cómo funciona:</b>\n"
            "1️⃣ <b>Depósito</b> — Recarga USDT una sola vez en tu billetera dedicada.\n"
            "2️⃣ <b>Crear</b> — Inicia una nueva apuesta y compártela en cualquier lugar.\n"
            "3️⃣ <b>Participar</b> — Apuesta en pools activos con solo un toque.\n"
            "4️⃣ <b>Ganar</b> — ¡Los premios se acreditan al instante!\n\n"
            "💳 <b>Sistema de Créditos</b>\n"
            "Haz <u>un solo depósito</u> y usa tus créditos para tantas apuestas como quieras, sin tarifas de gas. Retira siempre que quieras.\n\n"
            "👇 <b>Usa los botones de abajo para empezar</b> 👇"
        ),
        "bet_not_found": "❌ Apuesta no encontrada o caducada.",
        "deposit_tutorial": (
            "💳 <b>TUTORIAL DE DEPÓSITO - CÓMO RECARGAR</b>\n\n"
            "Para apostar en PoolBet, necesitas <b>USDT (Tether)</b> en la red <b>Polygon (MATIC)</b>.\nSigue estos pasos:\n\n"
            "<b>1️⃣ OBTÉN UNA BILLETERA O EXCHANGE</b>\n"
            "Si no tienes criptomonedas, descarga una aplicación como <b>Binance, Bybit, Coinbase o Crypto.com</b>. Regístrate y compra USDT usando moneda local (tarjeta/transferencia).\n\n"
            "<b>2️⃣ VE A RETIRO</b>\n"
            "Desde tu exchange, haz clic en: -> 'USDT' -> 'Retirar' -> 'Enviar a través de Red Cripto'.\n\n"
            "<b>3️⃣ CONFIGURA LOS DETALLES DE ENVÍO</b>\n"
            "▪️ <b>Dirección de Destino:</b> Haz clic abajo para copiarla:\n"
            "<code>{address}</code>\n"
            "▪️ <b>Red:</b> <tg-spoiler>POLYGON (MATIC)</tg-spoiler> ⚠️ <i>[CRUCIAL: ¡Debes seleccionar estrictamente Polygon, si eliges ERC20 o Tron perderás tus fondos!]</i>\n"
            "▪️ <b>Cantidad:</b> La cantidad que deseas depositar.\n\n"
            "<b>4️⃣ CONFIRMAR</b>\n"
            "Confirma el retiro. La red Polygon tarda en promedio de 1 a 3 minutos.\n\n"
            "<b>✅ ABONO AUTOMÁTICO</b>\n"
            "No necesitas hacer nada más. ¡Recibirás un mensaje aquí en el bot una vez que lleguen los fondos!\n\n"
            "🎁 <b>PROMOCIÓN</b>: ¡Cada depósito ≥ <b>50 USDT</b> recibe automáticamente un <b>Bono del +5%</b>!"
        ),
        "err_profile": "❌ Perfil no encontrado. Usa /start para registrarte.",
        "err_insufficient": "❌ Saldo insuficiente.",
        "err_bet_not_found": "❌ Apuesta no encontrada.",
        "err_invalid_option": "❌ Opción no válida.",
        "err_cancelled": "❌ Operación cancelada.",
        "err_generic": "❌ Error: {error}",
    },
    "pt": {
        # Comandos e Menu
        "menu_balance": "💰 Meu Saldo",
        "menu_create": "➕ Criar Aposta",
        "menu_explore": "🌐 Explorar",
        "menu_minigames": "🕹️ Mini-jogos",
        "menu_leaderboard": "🏆 Classificações",
        "btn_game_8ball": "🎱 Ball 8 (1-8)",
        "btn_game_mines": "💣 Mines",
        "btn_game_coinflip": "🪙 Cara ou Coroa",
        "btn_game_dice": "🎲 Dados",
        "game_8ball_title": "🎱 **Bilhar Ball 8 (1-8)**",
        "game_8ball_title": "🎱 **Bilhar Ball 8 (1-8)**",
        "game_8ball_descr": "Aposte num número entre 1 e 8. Se a bola parar no seu número, ganha **7x** a sua aposta!\nAs perdas revertem para o suporte da plataforma.",
        "game_8ball_bet": "💰 Aposta: <b>{amount} USDT</b>",
        "game_8ball_target": "🎯 Número escolhido: <b>{target}</b>",
        "game_8ball_win": "🎉 <b>VOCÊ GANHOU!</b>\nSaiu o número {num}.\nGanhou {win_amount} USDT!",
        "game_8ball_loss": "❌ <b>VOCÊ PERDEU</b>\nSaiu o número {num}.\nA sua aposta de {bet_amount} USDT foi para a plataforma.",
        "game_8ball_insufficient": "❌ Saldo insuficiente!",
        "btn_play": "🎰 JOGAR!",
        "menu_mybets": "📋 Minhas Apostas",
        "menu_help": "ℹ️ Ajuda / Info",
        
        # Criação de Aposta
        "prompt_question": "🎯 <b>Criar Aposta</b> — Passo 1/8\n\nInsira a <b>pergunta</b> da aposta.",
        "prompt_hashtags": "🏷️ <b>Adicionar Hashtag</b> — Passo 2/8\n\nCategorize a sua aposta com uma ou mais hashtags (ex: #futebol).\n<b>Obrigatório</b> para que seja encontrada na pesquisa.",
        "prompt_options": "📝 <b>Adicionar Opções</b> — Passo 4/8\n\nInsira as opções uma de cada vez (mín 2, máx 8).",
        "prompt_min_bet": "💧 <b>Liquidez Inicial</b> — Passo 5/8\n\nQuantos USDT quer colocar como pool base?\n<i>O valor será dividido igualmente pelas opções.</i>",
        "prompt_duration": "⏱ <b>Duração</b> — Passo 6/8\n\nQuanto tempo deve durar a aposta?",
        "prompt_privacy": "🕵️ <b>Visibilidade</b> — Passo 7/8\n\nQuer que a aposta seja visível no feed <b>Explorar</b> ou apenas via link direto?",
        "btn_public": "🌐 Pública (Feed Explorar)",
        "btn_private": "🔒 Privada (apenas Link)",
        "bet_created_success": "✅ <b>Aposta criada!</b>\n💧 Depositou {amount} USDT nas {opt_count} opções.\n\n🔗 Link direto:\n<code>{link}</code>\n\nPartilhe o link — quem o abrir pode participar instantaneamente!",
        "btn_share_group": "📢 Partilhar no Grupo",
        "btn_share": "🔗 Partilhar esta Aposta",
        "btn_search_tag": "🔍 Procurar por Tag",
        "btn_reset_search": "🌐 Fechar Pesquisa",
        "search_prompt": "🔍 <b>Motor de Pesquisa</b>\n\nEscreva a hashtag a pesquisar (ex: #futebol) ou envie 'cancelar'.",
        # Saldo e Wallet
        "btn_withdraw": "💸 Levantar",
        "btn_history": "📊 Histórico",
        "btn_copy_addr": "📋 Copiar Endereço",
        "btn_qr": "📷 Mostrar QR",
        "btn_deposit_info": "➕ Carregar (info)",
        "btn_daily": "🎁 Faucet Diário",
        "daily_success": "🎁 <b>FAUCET RECOLHIDO!</b>\n\nObteve <b>{bonus} USDT</b> em créditos bónus.\n🔥 Streak atual: <b>{streak} dias</b>\n⭐ XP Ganhos: <b>+{xp} XP</b>\n\n<i>Volte amanhã para aumentar o seu multiplicador!</i>",
        "daily_already": "⏳ Já recolheu o faucet de hoje.\n\n<i>O faucet reinicia à meia-noite (UTC).</i>",
        "btn_referral": "👥 Convidar um Amigo",
        "referral_text": (
            "👥 <b>Programa de Referenciamento</b>\n\n"
            "Convide os seus amigos e receba um bónus por cada novo utilizador que se registar!\n\n"
            "Aqui está o seu link único:\n<code>{link}</code>"
        ),
        "trust_score": "🛡️ Confiabilidade: <b>{score}%</b>",
        
        # Scommessa e Partecipazione
        "btn_cancel": "❌ Cancelar",
        "btn_confirm": "✅ Confirmar",
        "btn_custom_amount": "✏️ Inserir valor personalizado",
        "btn_close_bet": "🔒 Fechar Aposta",
        "btn_back_menu": "🔙 Voltar ao Menu",
        
        # Mance / Tipping
        "btn_tip": "💸 Enviar Gorjeta",
        "tip_ask_username": "💸 <b>Enviar Gorjeta</b>\n\nPara quem quer enviar os fundos? Insira o seu @username Telegram:",
        "tip_ask_amount": "💸 <b>Enviar gorjeta para @{username}</b>\n\nQuanto quer enviar em USDT?\n<i>(Será retida uma taxa de 5% para a plataforma)</i>",
        "tip_success": "✅ <b>Gorjeta Enviada!</b>\nEnviou {amount} USDT para @{username}.",
        "tip_received": "💸 <b>Gorjeta Recebida!</b>\nAcabou de receber <b>{amount} USDT</b> de @{sender}.",
        "err_user_not_found": "❌ Utilizador não encontrado. Certifique-se de que existe e iniciou o bot.",
        "err_self_tip": "❌ Não pode enviar uma gorjeta para si próprio!",
        "resolution_notification": "🔔 <b>Resultado Declarado!</b>\n\nScommessa: <i>{question}</i>\nResultado declarado pelo criador: <b>{winner}</b>\n\nVocê tem {hours} horas para contestar se acredita que o resultado é falso. A contestação exige um stake de {stake} USDT que você perderà se o protesto for infundado.",
        
        # Línguas
        "lang_updated": "✅ Idioma atualizado para Português!",
        "lang_prompt": "🌍 Selecione o seu idioma:",
        
        "welcome_text": (
            "👋 <b>Bem-vindo ao Pool8 Bot!</b>\n\n"
            "Crie as suas apostas públicas ou privadas, convide os seus amigos e gira o seu pool diretamente no Telegram.\n\n"
            "👇 <b>Use os botões abaixo para começar</b> 👇"
        ),
        "welcome_ticker": "🔥 <b>Recorde de Ganhos:</b> {ticker}\n\n",
        # Classifiche
        "leaderboard_title": "🏆 <b>RANKINGS POOL8</b>\n━━━━━━━━━━━━━━━━━━━━",
        "leaderboard_winners": "\n🥇 <b>Top Vencedores (últimos 7 dias)</b>",
        "leaderboard_creators": "\n🛡️ <b>Top Criadores (por Confiabilidade)</b>",
        "leaderboard_no_winners": "   Ainda sem ganhos esta semana.",
        "leaderboard_no_creators": "   Ainda sem criadores no ranking.",
        "leaderboard_footer": "\n━━━━━━━━━━━━━━━━━━━━\n🔄 Atualizado semanalmente. Crie e feche apostas para subir!",
        "bet_not_found": "❌ Aposta não encontrada ou expirada.",
        "deposit_tutorial": (
            "💳 <b>TUTORIAL DE CARREGAMENTO - COMO DEPOSITAR</b>\n\n"
            "Para apostar no PoolBet precisa de <b>USDT (Tether)</b> na rede <b>Polygon (MATIC)</b>.\nSiga estes passos:\n\n"
            "<b>1️⃣ OBTENHA UMA WALLET OU EXCHANGE</b>\n"
            "Se não tem criptomoedas, descarregue uma app como <b>Binance, Bybit, Coinbase ou Crypto.com</b>. Registe-se e compre USDT usando Euro (cartão/transferência).\n\n"
            "<b>2️⃣ VÁ A LEVANTAMENTO (WITHDRAW)</b>\n"
            "Na sua exchange, clique em: -> 'USDT' -> 'Levantar / Withdraw' -> 'Enviar via Rede Crypto'.\n\n"
            "<b>3️⃣ DEFINA OS DADOS DE ENVIO</b>\n"
            "▪️ <b>Endereço de Destino:</b> Clique abaixo para copiar:\n"
            "<code>{address}</code>\n"
            "▪️ <b>Rede (Network):</b> <tg-spoiler>POLYGON (MATIC)</tg-spoiler> ⚠️ <i>[FUNDAMENTAL: Escolha obrigatoriamente Polygon, se escolher ERC20 ou Tron perde os fundos!]</i>\n"
            "▪️ <b>Valor:</b> A quantia que deseja.\n\n"
            "<b>4️⃣ CONFIRME</b>\n"
            "Confirme o levantamento. A rede Polygon demora em média 1-3 minutos.\n\n"
            "<b>✅ CRÉDITO AUTOMÁTICO</b>\n"
            "Não precisa de fazer mais nada. Receberá uma mensagem aqui no bot assim que os fundos chegarem!\n\n"
            "🎁 <b>PROMOÇÃO</b>: Cada depósito ≥ <b>50 USDT</b> recebe automaticamente um <b>Bónus de +5%</b>!"
        ),
        "err_profile": "❌ Perfil não encontrado. Use /start para se registar.",
        "err_insufficient": "❌ Saldo insuficiente.",
        "err_bet_not_found": "❌ Aposta não encontrada.",
        "err_invalid_option": "❌ Opção inválida.",
        "err_cancelled": "❌ Operação cancelada.",
        "err_generic": "❌ Erro: {error}",
    }
}

def t(key: str, lang: str = "en", **kwargs) -> str:
    """
    Recupera la traduzione per la chiave specificata.
    Default a 'en' (Inglese) se la chiave non esiste nella lingua richiesta.
    """
    if lang not in TRANSLATIONS:
        lang = "en"
        
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text
