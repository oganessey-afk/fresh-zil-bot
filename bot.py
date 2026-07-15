import telebot
from telebot import types
import json
import os
import sys
import traceback
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
MY_ID = 1048444028

print(f"=== STARTUP === TOKEN set: {bool(TOKEN)}, WEBHOOK_URL: {WEBHOOK_URL}", flush=True)

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)


def handle_start(message):
    print(f"=== /start received from {message.from_user.id} ===", flush=True)
    try:
        name = message.from_user.first_name
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        shop_button = types.KeyboardButton(
            text="🛒 Открыть магазин Fresh Zil",
            web_app=types.WebAppInfo(url="https://eclectic-jelly-b961c0.netlify.app")
        )
        markup.add(shop_button)
        bot.send_message(
            message.chat.id,
            f"Привет, {name}! 👋\nДобро пожаловать в Fresh Zil 🍊\nСвежие продукты с рынка — прямо к вашей двери!",
            reply_markup=markup
        )
        print("=== /start: message sent OK ===", flush=True)
    except Exception as e:
        print(f"=== ERROR in handle_start: {e} ===", flush=True)
        traceback.print_exc(file=sys.stdout)


def handle_web_app_data(message):
    print("ПРИШЁЛ ЗАКАЗ:", message.web_app_data.data, flush=True)
    try:
        data = json.loads(message.web_app_data.data)
        name = message.from_user.first_name
        username = message.from_user.username
        order_text = "🛒 НОВЫЙ ЗАКАЗ!\n\n"
        order_text += f"От: {name}"
        if username:
            order_text += f" (@{username})"
        order_text += "\n\n"
        for item in data['items']:
            order_text += f"• {item['name']} — {item['price']} ₽\n"
        order_text += f"\nИтого: {data['total']} ₽"
        bot.send_message(MY_ID, order_text)
        bot.send_message(message.chat.id, f"Спасибо за заказ, {name}! 🌿")
    except Exception as e:
        print(f"=== ERROR in handle_web_app_data: {e} ===", flush=True)
        traceback.print_exc(file=sys.stdout)


def dispatch_update(update):
    """Manually route the update to the right handler, bypassing process_new_updates."""
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
