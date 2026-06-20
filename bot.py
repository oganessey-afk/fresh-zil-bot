import telebot
from telebot import types
import json
import os
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
MY_ID = 1048444028

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


@bot.message_handler(commands=['start'])
def welcome(message):
    name = message.from_user.first_name
    markup = types.InlineKeyboardMarkup()
    shop_button = types.InlineKeyboardButton(
        text="🛒 Открыть магазин Fresh Zil",
        web_app=types.WebAppInfo(url="https://eclectic-jelly-b961c0.netlify.app")
    )
    markup.add(shop_button)
    bot.send_message(
        message.chat.id,
        f"Привет, {name}! 👋\nДобро пожаловать в Fresh Zil 🍊\nСвежие продукты с рынка — прямо к вашей двери!",
        reply_markup=markup
    )


@bot.message_handler(content_types=['web_app_data'])
def get_order(message):
    print("ПРИШЁЛ ЗАКАЗ:", message.web_app_data.data)
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
    bot.send_message(message.chat.id, "Спасибо за заказ! 🌿 Мы скоро свяжемся с вами для подтверждения.")


@app.route('/webhook', methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200


@app.route('/', methods=['GET'])
def index():
    return 'Fresh Zil bot is running', 200


@app.route('/set_webhook', methods=['GET'])
def set_webhook_route():
    bot.remove_webhook()
    if WEBHOOK_URL and TOKEN:
        bot.set_webhook(url=WEBHOOK_URL + '/webhook')
        return f"Webhook установлен: {WEBHOOK_URL}/webhook", 200
    return "ВНИМАНИЕ: WEBHOOK_URL или BOT_TOKEN не задан!", 500


if __name__ == '__main__':
    bot.remove_webhook()
    if WEBHOOK_URL and TOKEN:
        bot.set_webhook(url=WEBHOOK_URL + '/webhook')
        print("Webhook установлен:", WEBHOOK_URL + '/webhook')
    else:
        print("ВНИМАНИЕ: WEBHOOK_URL или BOT_TOKEN не задан!")
    port = int(os.environ.get('PORT', 80))
    app.run(host='0.0.0.0', port=port)
