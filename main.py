from keep_alive import keep_alive
import telebot
from telebot import types
import random
import threading
import time

TOKEN = "8161107014:AAH1I0srDbneOppDw4AsE2kEYtNtk7CRjOw"
bot = telebot.TeleBot(TOKEN)

user_balances = {}
user_games = {}
user_aviator_games = {}
ADMIN_ID = 5815294733
withdraw_sessions = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_balances.setdefault(user_id, 1000)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Balance', 'Play Mines')
    markup.add('Play Aviator', 'hisob toldirish')
    bot.send_message(message.chat.id, "Xush kelibsiz! O'yinni tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Balance")
def balance(message):
    user_id = message.from_user.id
    bal = user_balances.get(user_id, 0)
    bot.send_message(message.chat.id, f"Balansingiz: {bal} so‘m")

@bot.message_handler(func=lambda m: m.text == "Play Mines")
def start_mines(message):
    user_id = message.from_user.id
    if user_id in user_games:
        bot.send_message(message.chat.id, "Avvalgi o‘yinni tugating yoki pulni yeching.")
        return
    msg = bot.send_message(message.chat.id, "Stavka miqdorini kiriting (min 1000):")
    bot.register_next_step_handler(msg, init_mines)

def init_mines(message):
    try:
        user_id = message.from_user.id
        stake = int(message.text)
        if stake < 500:
            bot.send_message(message.chat.id, "Kamida 1000 so‘m tikish kerak.")
            return
        if user_balances.get(user_id, 0) < stake:
            bot.send_message(message.chat.id, "Yetarli balans yo‘q.")
            return

        user_balances[user_id] -= stake
        bombs = random.sample(range(25), 3)
        user_games[user_id] = {
            'stake': stake,
            'bombs': bombs,
            'opened': [],
            'multiplier': 1.0
        }
        send_mines_board(message.chat.id, user_id, bomb_triggered=False)

    except ValueError:
        bot.send_message(message.chat.id, "Raqam kiriting.")

def send_mines_board(chat_id, user_id, bomb_triggered=False):
    game = user_games.get(user_id)
    if not game:
        return

    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = []

    for i in range(25):
        if i in game['opened']:
            btn = types.InlineKeyboardButton("OK", callback_data="ignore")
        else:
            btn = types.InlineKeyboardButton(str(i + 1), callback_data=f"open_{i}")
        buttons.append(btn)

    for i in range(0, 25, 5):
        markup.row(*buttons[i:i + 5])

    if not bomb_triggered:
        markup.add(types.InlineKeyboardButton("Pulni yechish", callback_data="cashout"))

    text = f"""MINES O'yini
Bombalar: 3
Stavka: {game['stake']} so‘m
Multiplikator: x{round(game['multiplier'], 2)}"""
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id not in user_games:
        bot.answer_callback_query(call.id, "O‘yin topilmadi.")
        return

    game = user_games[user_id]

    if call.data == "cashout":
        win = min(int(game['stake'] * game['multiplier']), int(game['stake'] * 2))
        user_balances[user_id] += win
        del user_games[user_id]
        bot.edit_message_text(f"{win} so‘m yutdingiz! Tabriklaymiz!", call.message.chat.id, call.message.message_id)
        return

    if call.data.startswith("open_"):
        idx = int(call.data.split("_")[1])
        if idx in game['opened']:
            bot.answer_callback_query(call.id, "Bu katak ochilgan.")
            return

        if idx in game['bombs']:
            game['opened'] = list(set(game['opened'] + game['bombs']))
            send_mines_board(call.message.chat.id, user_id, bomb_triggered=True)
            del user_games[user_id]
            bot.edit_message_text("Bomba topildi! Siz yutqazdingiz keyingi safar yutasiz.", call.message.chat.id, call.message.message_id)
            return

        game['opened'].append(idx)
        game['multiplier'] *= 1.08
        send_mines_board(call.message.chat.id, user_id, bomb_triggered=False)

@bot.message_handler(func=lambda m: m.text == "hisob toldirish")
def pay(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "shu odamga murojat qilinglar @for_X_bott")
        return
    msg = bot.send_message(message.chat.id, "Foydalanuvchi ID sini yozing:")
    bot.register_next_step_handler(msg, ask_amount)

def ask_amount(message):
    try:
        user_id = int(message.text)
        msg = bot.send_message(message.chat.id, "Qancha pul qo‘shamiz?")
        bot.register_next_step_handler(msg, lambda m: add_balance(m, user_id))
    except ValueError:
        bot.send_message(message.chat.id, "ID noto‘g‘ri.")

def add_balance(message, user_id):
    try:
        amount = int(message.text)
        user_balances[user_id] = user_balances.get(user_id, 0) + amount
        bot.send_message(message.chat.id, f"{amount} so‘m {user_id} ga qo‘shildi.")
    except ValueError:
        bot.send_message(message.chat.id, "Miqdor noto‘g‘ri.")

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.send_message(message.chat.id, f"ID: {message.from_user.id}")

@bot.message_handler(commands=['withdraw'])
def withdraw_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, " Bu buyruq faqat admin uchun.")
        return

    withdraw_sessions[message.from_user.id] = {}
    msg = bot.send_message(message.chat.id, " Foydalanuvchi ID raqamini kiriting:")
    bot.register_next_step_handler(msg, process_withdraw_user_id)

def process_withdraw_user_id(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text)
        withdraw_sessions[message.from_user.id]['user_id'] = user_id
        msg = bot.send_message(message.chat.id, " Qancha pul yechib beramiz?")
        bot.register_next_step_handler(msg, process_withdraw_amount)
    except ValueError:
        bot.send_message(message.chat.id, " ID noto‘g‘ri. Raqam kiriting.")

def process_withdraw_amount(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        amount = int(message.text)
        session = withdraw_sessions.get(message.from_user.id, {})
        user_id = session.get('user_id')

        if user_id is None:
            bot.send_message(message.chat.id, " Avval foydalanuvchi ID kiriting.")
            return

        if user_balances.get(user_id, 0) < amount:
            bot.send_message(message.chat.id, " Bu foydalanuvchining balansida yetarli mablag‘ yo‘q.")
            return

        user_balances[user_id] -= amount
        bot.send_message(message.chat.id, f" {user_id} balansidan {amount} so‘m yechildi. Qolgan: {user_balances[user_id]}")

        try:
            bot.send_message(user_id, f" Sizning balansingizdan {amount} so‘m yechildi.")
        except:
            pass

        withdraw_sessions.pop(message.from_user.id, None)

    except ValueError:
        bot.send_message(message.chat.id, " Miqdor noto‘g‘ri. Raqam kiriting.")

# === Aviator ===
@bot.message_handler(func=lambda m: m.text == "Play Aviator")
def aviator(message):
    user_id = message.from_user.id
    if user_id in user_aviator_games and user_aviator_games[user_id]['running']:
        bot.send_message(user_id, " O'yin allaqachon ishlamoqda! /stop deb to'xtat.")
        return
    msg = bot.send_message(user_id, " Nech pul tikmoqchisiz?")
    bot.register_next_step_handler(msg, process_aviator_bet)

def process_aviator_bet(message):
    user_id = message.from_user.id
    try:
        bet = int(message.text)
        if bet <= 0:
            raise ValueError
        if user_balances.get(user_id, 0) < bet:
            bot.send_message(user_id, " Hisobingizda yetarli mablag' yo'q.")
            return
        user_balances[user_id] -= bet
        user_aviator_games[user_id] = {'bet': bet, 'multiplier': 1.0, 'running': True}
        bot.send_message(user_id, f" O'yin boshlandi! /stop yuborib pulni chiqarib oling.")
        threading.Thread(target=run_aviator_game, args=(user_id,)).start()
    except ValueError:
        bot.send_message(user_id, " Iltimos, to‘g‘ri son kiriting.")

def run_aviator_game(user_id):
    game = user_aviator_games[user_id]
    crash_point = round(random.uniform(1.01, 3.0), 2)
    while game['running']:
        time.sleep(1)
        game['multiplier'] += round(random.uniform(0.1, 0.3), 2)
        if game['multiplier'] >= crash_point:
            game['running'] = False
            bot.send_message(user_id, f" Crash! Multiplier: {game['multiplier']}x. Siz pulni chiqarishga ulgurmadingiz.")
            return
        bot.send_message(user_id, f" {round(game['multiplier'], 2)}x")

@bot.message_handler(commands=['stop'])
def stop_aviator(message):
    user_id = message.from_user.id
    game = user_aviator_games.get(user_id)
    if not game or not game['running']:
        bot.send_message(user_id, " Hozirda Aviator o'yini yo'q.")
        return

    game['running'] = False
    win_amount = int(game['bet'] * game['multiplier'])
    user_balances[user_id] = user_balances.get(user_id, 0) + win_amount
    bot.send_message(user_id, f" Tabriklaymiz! Siz {round(game['multiplier'], 2)}x bilan {win_amount} so‘m yutdingiz.")

# === YAKUNI ===
print("Bot ishga tushdi...")
keep_alive()
bot.polling(none_stop=True)
