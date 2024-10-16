import telebot
import config
import os
from telebot import types
from threading import Lock  # To ensure thread safety

bot = telebot.TeleBot(config.TOKEN)

# Admin chat ID (your user ID)
ADMIN_CHAT_ID = 551429608

# New menu of drink options
menu = ["Iced Matcha Latte", "Iced Houjicha Latte", "Iced Chocolate", "Surprise Drink"]

# Store each user's order and state
user_data = {}

# Queue counter file
QUEUE_FILE = "queue_counter.txt"
queue_lock = Lock()  # Lock to ensure thread-safe operations

# File ID for the menu image
MENU_IMAGE_FILE_ID = 'AgACAgUAAxkBAAID3GcPGWk99TJab_qnKizpnIrVjrtZAAIFvzEbnQZ5VP7M3JiITBziAQADAgADeQADNgQ'

# Load the queue number from the file or initialize it
def load_queue_number():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r') as file:
            try:
                return int(file.read().strip())
            except ValueError:
                save_queue_number(1)
                return 1
    return 1

# Save the updated queue number to the file
def save_queue_number(number):
    with open(QUEUE_FILE, 'w') as file:
        file.write(str(number))

queue_number = load_queue_number()

@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {
        "answers": [], 
        "drink_orders": [], 
        "message_ids": [], 
        "username": message.from_user.username, 
        "state": "START"
    }

    welcome_text = (
        "Hello! Welcome to the Battambar Order Bot. We are selling Iced Matcha, "
        "Iced Chocolate, Iced Houjicha Latte, and a Surprise Drink. "
        "Each cup is 4 dollars, and there is 1 dollar off for every 3 drinks. "
        "Our surprise drink is 5 dollars ;)"
    )
    msg = bot.send_message(chat_id, welcome_text)
    user_data[chat_id]["message_ids"].append(msg.message_id)

    menu_msg = bot.send_photo(chat_id, MENU_IMAGE_FILE_ID)
    user_data[chat_id]["message_ids"].append(menu_msg.message_id)

    ask_question(message, 0)

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

def show_menu(message):
    chat_id = message.chat.id
    user_data[chat_id]["state"] = "CHOOSING_DRINK"

    markup = types.InlineKeyboardMarkup()
    for drink in menu:
        markup.add(types.InlineKeyboardButton(drink, callback_data=drink))

    msg = bot.send_message(chat_id, "Please select a drink:", reply_markup=markup)
    user_data[chat_id]["message_ids"].append(msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data in menu)
def handle_menu_selection(call):
    chat_id = call.message.chat.id
    if user_data[chat_id]["state"] == "CHOOSING_DRINK":
        selected_drink = call.data
        user_data[chat_id]["answers"].append(selected_drink)

        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

        msg = bot.send_message(chat_id, f"How many {selected_drink} would you like?")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        user_data[chat_id]["state"] = "CHOOSING_QUANTITY"
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

def handle_quantity_selection(message, selected_drink):
    chat_id = message.chat.id
    try:
        quantity = int(message.text)
        if quantity < 1:
            raise ValueError

        user_data[chat_id]["drink_orders"].append(f"{quantity} x {selected_drink}")

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Yes", callback_data="yes_more_drinks"))
        markup.add(types.InlineKeyboardButton("No", callback_data="no_more_drinks"))

        msg = bot.send_message(chat_id, "Would you like to order more drinks?", reply_markup=markup)
        user_data[chat_id]["message_ids"].append(msg.message_id)
        user_data[chat_id]["state"] = "MORE_DRINKS"

    except ValueError:
        msg = bot.send_message(chat_id, "Invalid input. Please enter a valid number.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

@bot.callback_query_handler(func=lambda call: call.data in ["yes_more_drinks", "no_more_drinks"])
def handle_more_drinks(call):
    chat_id = call.message.chat.id

    if call.data == "yes_more_drinks":
        show_menu(call.message)
    else:
        if user_data[chat_id]["state"] != "AWAITING_PAYMENT":
            user_data[chat_id]["state"] = "AWAITING_PAYMENT"
            msg = bot.send_message(
                chat_id,
                "Please PayNow Reiyean +6592331010 and upload the payment confirmation photo.\n\n"
                "Support our scholarship program for underprivileged children—"
                "feel free to contribute more and make a difference today!"
            )
            user_data[chat_id]["message_ids"].append(msg.message_id)
            bot.register_next_step_handler(msg, handle_payment_confirmation)

def handle_payment_confirmation(message):
    chat_id = message.chat.id

    if user_data[chat_id]["state"] != "AWAITING_PAYMENT":
        bot.send_message(chat_id, "Payment has already been processed.")
        return

    if message.content_type == 'photo':
        with queue_lock:
            global queue_number
            order_queue_number = queue_number
            queue_number += 1
            save_queue_number(queue_number)

        user_data[chat_id]["state"] = "PAYMENT_CONFIRMED"
        user_data[chat_id]["queue_number"] = order_queue_number

        handle_picture(message, order_queue_number)
    else:
        msg = bot.send_message(chat_id, "Please upload a valid photo for payment confirmation.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_payment_confirmation)

def handle_picture(message, order_queue_number):
    chat_id = message.chat.id
    photo_id = message.photo[-1].file_id

    name = user_data[chat_id]["answers"][0]
    telegram_handle = user_data[chat_id]["answers"][1]
    drink_orders = "\n".join(user_data[chat_id]["drink_orders"])

    caption_text = (
        f"New Order:\n"
        f"{name}\n"
        f"{telegram_handle}\n"
        f"{drink_orders}\n"
        f"Queue Number: #{order_queue_number}"
    )

    bot.send_photo(chat_id, photo_id, caption=f"Order Summary:\n{caption_text}")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{chat_id}"))

    bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=caption_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    bot.answer_callback_query(call.id)

    try:
        user_chat_id = int(call.data.split("_")[-1])
        if user_chat_id not in user_data:
            bot.send_message(call.message.chat.id, "Order already processed or user not found.")
            return

        username = user_data[user_chat_id]["username"]

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Ready", callback_data="none"))

        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.send_message(user_chat_id, "Your order is ready for collection!")
        bot.send_message(call.message.chat.id, f"The user @{username} has been informed.")

        clear_user_messages(user_chat_id)
        del user_data[user_chat_id]

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error processing the order: {str(e)}")

def clear_user_messages(chat_id):
    for msg_id in user_data[chat_id]["message_ids"]:
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    user_data[chat_id]["message_ids"].clear()

@bot.message_handler(commands=['reset_queue'])
def reset_queue(message):
    if message.chat.id == ADMIN_CHAT_ID:
        save_queue_number(1)
        bot.send_message(message.chat.id, "Queue number has been reset to 1.")

bot.polling(none_stop=True, interval=0, timeout=20)
