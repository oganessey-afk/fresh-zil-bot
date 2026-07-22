import telebot
from telebot import types
import json
import os
import sys
import traceback
import requests
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
MY_ID = 1048444028

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

print(f"=== STARTUP === TOKEN set: {bool(TOKEN)}, WEBHOOK_URL: {WEBHOOK_URL}", flush=True)

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# Временное хранилище для диалогов сбора данных
user_states = {}


def supabase_get_customer(telegram_id):
    """Получить данные клиента из Supabase"""
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/customers?telegram_id=eq.{telegram_id}",
            headers=headers
        )
        data = res.json()
        if data:
            return data[0]
        return None
    except Exception as e:
        print(f"=== ERROR supabase_get_customer: {e} ===", flush=True)
        return None


def supabase_save_customer(telegram_id, first_name, phone, apartment):
    """Сохранить или обновить данные клиента в Supabase"""
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        data = {
            "telegram_id": telegram_id,
            "first_name": first_name,
            "phone": phone,
            "apartment": apartment
        }
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=headers,
            json=data
        )
        print(f"=== Supabase save: {res.status_code} ===", flush=True)
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"=== ERROR supabase_save_customer: {e} ===", flush=True)
        return False


def send_shop_button(chat_id, name):
    """Отправить приветствие с кнопкой магазина"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    shop_button = types.KeyboardButton(
        text="🛒 Открыть магазин Fresh Zil",
        web_app=types.WebAppInfo(url="https://eclectic-jelly-b961c0.netlify.app")
    )
    markup.add(shop_button)
    bot.send_message(
        chat_id,
        f"Привет, {name}! 👋\nДобро пожаловать в Fresh Zil 🍊\nСвежие продукты с рынка — прямо к вашей двери!",
        reply_markup=markup
    )


def handle_start(message):
    print(f"=== /start received from {message.from_user.id} ===", flush=True)
    try:
        telegram_id = message.from_user.id
        name = message.from_user.first_name
        send_shop_button(message.chat.id, name)
        print("=== /start: message sent OK ===", flush=True)
    except Exception as e:
        print(f"=== ERROR in handle_start: {e} ===", flush=True)
        traceback.print_exc(file=sys.stdout)


def handle_web_app_data(message):
    print("ПРИШЁЛ ЗАКАЗ:", message.web_app_data.data, flush=True)
    try:
        data = json.loads(message.web_app_data.data)
        telegram_id = message.from_user.id
        name = message.from_user.first_name
        username = message.from_user.username

        # Читаем данные клиента из заказа (заполнены в форме магазина)
        customer_data = data.get('customer', {})
        customer_name = customer_data.get('name') or name
        phone = customer_data.get('phone', 'не указан')
        apartment = customer_data.get('apartment', 'не указана')

        # Сохраняем данные в Supabase
        if customer_data:
            supabase_save_customer(telegram_id, customer_name, phone, apartment)

        # Формируем текст заказа
        order_text = "🛒 НОВЫЙ ЗАКАЗ!\n\n"
        order_text += f"От: {customer_name}"
        if username:
            order_text += f" (@{username})"
        order_text += f"\n📱 Телефон: {phone}"
        order_text += f"\n🏠 Квартира: {apartment}"
        order_text += "\n\n"
        for item in data['items']:
            qty = item.get('qty', 1)
            order_text += f"• {item['name']} × {qty} — {item['price'] * qty} ₽\n"
        order_text += f"\nИтого: {data['total']} ₽"

        bot.send_message(MY_ID, order_text)
        bot.send_message(
            message.chat.id,
            f"Спасибо за заказ, {customer_name}! 🌿\nМы всё получили и скоро приступим к сборке."
        )

    except Exception as e:
        print(f"=== ERROR in handle_web_app_data: {e} ===", flush=True)
        traceback.print_exc(file=sys.stdout)


def process_order(message, data, customer):
    """Обработать заказ и отправить уведомление"""
    telegram_id = message.from_user.id
    name = customer.get('first_name') or message.from_user.first_name
    username = message.from_user.username
    phone = customer.get('phone', 'не указан')
    apartment = customer.get('apartment', 'не указана')

    order_text = "🛒 НОВЫЙ ЗАКАЗ!\n\n"
    order_text += f"От: {name}"
    if username:
        order_text += f" (@{username})"
    order_text += f"\n📱 Телефон: {phone}"
    order_text += f"\n🏠 Квартира: {apartment}"
    order_text += "\n\n"
    for item in data['items']:
        qty = item.get('qty', 1)
        order_text += f"• {item['name']} × {qty} — {item['price'] * qty} ₽\n"
    order_text += f"\nИтого: {data['total']} ₽"

    bot.send_message(MY_ID, order_text)
    bot.send_message(
        message.chat.id,
        f"Спасибо за заказ, {name}! 🌿\nМы всё получили и скоро приступим к сборке."
    )


def handle_text(message):
    """Обработка текстовых сообщений (сбор данных клиента)"""
    telegram_id = message.from_user.id
    state_data = user_states.get(telegram_id)

    if not state_data:
        return

    state = state_data.get('state')

    if state == 'waiting_phone':
        # Сохраняем телефон, просим квартиру
        user_states[telegram_id]['phone'] = message.text
        user_states[telegram_id]['state'] = 'waiting_apartment'
        bot.send_message(
            message.chat.id,
            "🏠 Введите номер вашей квартиры:"
        )

    elif state == 'waiting_apartment':
        # Сохраняем квартиру, записываем в Supabase
        phone = user_states[telegram_id].get('phone')
        apartment = message.text
        name = user_states[telegram_id].get('name') or message.from_user.first_name
        order_data = user_states[telegram_id].get('order_data')

        # Сохраняем в Supabase
        supabase_save_customer(telegram_id, name, phone, apartment)

        # Убираем состояние
        del user_states[telegram_id]

        # Обрабатываем заказ
        customer = {
            'first_name': name,
            'phone': phone,
            'apartment': apartment
        }
        process_order(message, order_data, customer)


def dispatch_update(update):
    print(f"=== DISPATCH: update_id={update.update_id} ===", flush=True)
    message = update.message
    if message is None:
        print("=== DISPATCH: no message in update, skipping ===", flush=True)
        return

    print(f"=== DISPATCH: content_type={message.content_type}, text={getattr(message, 'text', None)} ===", flush=True)

    if message.content_type == 'text' and message.text and message.text.startswith('/start'):
        handle_start(message)
    elif message.content_type == 'web_app_data':
        handle_web_app_data(message)
    elif message.content_type == 'text':
        handle_text(message)
    else:
        print(f"=== DISPATCH: unhandled message, content_type={message.content_type} ===", flush=True)


@app.route('/webhook', methods=['POST'])
def receive_update():
    try:
        json_string = request.get_data().decode('utf-8')
        print(f"=== WEBHOOK RAW DATA: {json_string[:500]} ===", flush=True)
        update = telebot.types.Update.de_json(json_string)
        dispatch_update(update)
    except Exception as e:
        print(f"=== ERROR in /webhook route: {e} ===", flush=True)
        traceback.print_exc(file=sys.stdout)
    return '', 200


@app.route('/', methods=['GET'])
def index():
    return 'Fresh Zil bot is running', 200


@app.route('/set_webhook', methods=['GET'])
def set_webhook_route():
    try:
        bot.remove_webhook()
        if WEBHOOK_URL and TOKEN:
            bot.set_webhook(url=WEBHOOK_URL + '/webhook')
            return f"Webhook установлен: {WEBHOOK_URL}/webhook", 200
        return "ВНИМАНИЕ: WEBHOOK_URL или BOT_TOKEN не задан!", 500
    except Exception as e:
        return f"ОШИБКА при установке webhook: {e}", 500


if __name__ == '__main__':
    bot.remove_webhook()
    if WEBHOOK_URL and TOKEN:
        bot.set_webhook(url=WEBHOOK_URL + '/webhook')
        print("Webhook установлен:", WEBHOOK_URL + '/webhook')
    else:
        print("ВНИМАНИЕ: WEBHOOK_URL или BOT_TOKEN не задан!")
    port = int(os.environ.get('PORT', 80))
    app.run(host='0.0.0.0', port=port)
