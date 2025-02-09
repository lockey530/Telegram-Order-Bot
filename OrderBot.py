import telebot
import os
from telebot import types
from flask import Flask, request
from threading import Lock

# New bot token
TOKEN = "7859995354:AAHKDZChcNL4dDMU9As_hJBwjIN0uXAuuYM"
bot = telebot.TeleBot(TOKEN)

# List of admin chat IDs
ADMIN_CHAT_IDS = [551429608, 881189472]

# Updated Menu
menu = {"Drinks": ["Strawberry-ade", "Strawberry Matcha", "Iced Matcha Latte", "Iced Chocolate"]}
pricing = {"Strawberry-ade": 3, "Strawberry Matcha": 4.5, "Iced Matcha Latte": 4, "Iced Chocolate": 4}
macarons_pricing = {"Macarons - 3 for $7": 7, "Macarons - 6 for $12": 12}

# User data and queue handling
user_data = {}
QUEUE_FILE = "queue_counter.txt"
queue_lock = Lock()
MENU_IMAGE_FILE_ID = 'AgACAgUAAxkBAAIcmGeo14cqE7OgKCww1gudTn4UJYrgAAI91DEbPplJVYe07NscXNsZAQADAgADeQADNgQ'

# Flask app to handle webhooks
app = Flask(__name__)

# Load queue number from the file
def load_queue_number():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r') as file:
            try:
                return int(file.read().strip())
            except ValueError:
                save_queue_number(1)
                return 1
    return 1

def save_queue_number(number):
    with open(QUEUE_FILE, 'w') as file:
        file.write(str(number))

queue_number = load_queue_number()

# Webhook route to handle incoming updates from Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Receive updates from Telegram."""
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# Handle the /start command
@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {
        "answers": [], "drink_orders": [], 
        "message_ids": [], "username": message.from_user.username, 
        "state": "START", "order_finalized": False
    }

    msg = bot.send_message(chat_id, "Welcome to Battam Bar Valentine's Specials! Drinks and macarons will be prepared at the counter. Please collect them when notified.")
    user_data[chat_id]["message_ids"].append(msg.message_id)

    menu_msg = bot.send_photo(chat_id, MENU_IMAGE_FILE_ID)
    user_data[chat_id]["message_ids"].append(menu_msg.message_id)

    ask_question(message, 0)

# Ask for user details
def ask_question(message, question_index):
    chat_id = message.chat.id
    questions = ["Please enter your name:", "Please enter your Telegram handle:"]

    if question_index < len(questions):
        msg = bot.send_message(chat_id, questions[question_index])
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_answer, question_index)
    else:
        show_menu(message)

def handle_answer(message, question_index):
    chat_id = message.chat.id
    user_data[chat_id]["answers"].append(message.text)
    user_data[chat_id]["message_ids"].append(message.message_id)
    ask_question(message, question_index + 1)

# Show the updated menu
def show_menu(message):
    chat_id = message.chat.id
    user_data[chat_id]["state"] = "CHOOSING_ITEM"

    markup = types.InlineKeyboardMarkup()
    for drink in menu["Drinks"]:
        markup.add(types.InlineKeyboardButton(drink, callback_data=f"drink_{drink}"))
    
    for option, price in macarons_pricing.items():
        markup.add(types.InlineKeyboardButton(option, callback_data=f"macarons_{option}"))

    msg = bot.send_message(chat_id, "Please select an item:", reply_markup=markup)
    user_data[chat_id]["message_ids"].append(msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("drink_"))
def handle_drink_selection(call):
    chat_id = call.message.chat.id
    selected_drink = call.data.split("_")[1]
    user_data[chat_id]["selected_drink"] = selected_drink

    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    finalize_order(chat_id, selected_drink, pricing[selected_drink])

@bot.callback_query_handler(func=lambda call: call.data.startswith("macarons_"))
def handle_macarons_selection(call):
    chat_id = call.message.chat.id
    selected_option = call.data.split("_")[1]
    user_data[chat_id]["selected_item"] = selected_option

    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    finalize_order(chat_id, selected_option, macarons_pricing[selected_option])

# Finalize the order
def finalize_order(chat_id, item, price):
    order = f"{item} (${price})"

    if order not in user_data[chat_id]["drink_orders"]:
        user_data[chat_id]["drink_orders"].append(order)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Yes", callback_data="yes_more_items"))
    markup.add(types.InlineKeyboardButton("No", callback_data="no_more_items"))

    msg = bot.send_message(chat_id, f"You have selected: {order}. Would you like to order more items?", reply_markup=markup)
    user_data[chat_id]["message_ids"].append(msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data in ["yes_more_items", "no_more_items"])
def handle_more_items(call):
    chat_id = call.message.chat.id
    if call.data == "yes_more_items":
        show_menu(call.message)
    else:
        request_payment(chat_id)

# Request payment
def request_payment(chat_id):
    total_amount = sum(float(order.split(" ($")[1].rstrip(")")) for order in user_data[chat_id]["drink_orders"])
    user_data[chat_id]["state"] = "AWAITING_PAYMENT"

    msg = bot.send_message(
        chat_id,
        f"Your total is ${total_amount:.2f}. Please PayNow to +6592331010.\n\n"
        "Once the transaction is complete, upload a screenshot of the payment confirmation here."
    )
    user_data[chat_id]["message_ids"].append(msg.message_id)
    bot.register_next_step_handler(msg, handle_payment_confirmation)

# Handle payment confirmation
def handle_payment_confirmation(message):
    chat_id = message.chat.id

    if message.content_type == 'photo' and user_data[chat_id]["state"] == "AWAITING_PAYMENT":
        user_data[chat_id]["state"] = "PAYMENT_CONFIRMED"

        bot.send_message(chat_id, "Payment confirmed! Your order is being processed.")
        process_final_order(chat_id)
    else:
        bot.send_message(chat_id, "Please upload a valid payment confirmation screenshot.")

# Process final order after payment confirmation
def process_final_order(chat_id):
    with queue_lock:
        global queue_number
        order_queue_number = queue_number
        queue_number += 1
        save_queue_number(queue_number)

    name = user_data[chat_id]["answers"][0]
    telegram_handle = user_data[chat_id]["answers"][1]
    orders = "\n".join(user_data[chat_id]["drink_orders"])

    caption_text = (
        f"Order Summary:\n{name}\n@{telegram_handle}\n{orders}\nQueue Number: #{order_queue_number}"
    )

    bot.send_message(chat_id, caption_text)

    for admin_id in ADMIN_CHAT_IDS:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{chat_id}"))
        bot.send_message(admin_id, f"New Order:\n{caption_text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    bot.answer_callback_query(call.id)

    user_chat_id = int(call.data.split("_")[-1])
    username = user_data[user_chat_id]["username"]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Ready", callback_data="none"))

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    bot.send_message(user_chat_id, "Your order is ready for collection! Enjoy your drink!")
    bot.send_message(call.message.chat.id, f"The user @{username} has been informed.")

@bot.message_handler(commands=['reset_queue'])
def reset_queue(message):
    if message.chat.id in ADMIN_CHAT_IDS:
        save_queue_number(1)
        bot.send_message(message.chat.id, "Queue number has been reset to 1.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
