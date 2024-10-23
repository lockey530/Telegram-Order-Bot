import telebot
import config
import os
from telebot import types
from threading import Lock  # To ensure thread safety

bot = telebot.TeleBot(config.TOKEN)

# List of admin chat IDs (replace with actual Telegram user IDs)
ADMIN_CHAT_IDS = [551429608, 881189472]  # Add more admin IDs as needed

# Updated menu structure
menu = {
    "Soft Drinks": ["Coca-Cola", "Coca-Cola Zero", "Sprite", "F&N Orange", "Coffee", "Tea"],
    "Liquor": ["Tiger Beer", "Vodka", "Whiskey", "Rum", "Gin"]
}

# Store each user's order and state
user_data = {}

# Queue counter file and lock for thread-safe queue operations
QUEUE_FILE = "queue_counter.txt"
queue_lock = Lock()

# File ID for the menu image
MENU_IMAGE_FILE_ID = 'AgACAgUAAxkBAAIMwGcYcU5hRcX49m1PlXZZZI_H4qmmAAJPvTEbMwPBVLBRAiCOhyJkAQADAgADeQADNgQ'

# Load queue number from file
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

@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {
        "answers": [], "drink_orders": [], 
        "message_ids": [], "username": message.from_user.username, 
        "state": "START"
    }

    msg = bot.send_message(chat_id, "Welcome to the Epoque Drinks Order Bot! Please note that these drinks will be prepared at the open bar. Please come to the open bar and collect it when the bot prompts you to do so!")
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
        show_category_menu(message)

def handle_answer(message, question_index):
    chat_id = message.chat.id
    user_data[chat_id]["answers"].append(message.text)
    user_data[chat_id]["message_ids"].append(message.message_id)
    ask_question(message, question_index + 1)

def show_category_menu(message):
    chat_id = message.chat.id
    user_data[chat_id]["state"] = "CHOOSING_CATEGORY"

    markup = types.InlineKeyboardMarkup()
    for category in menu.keys():
        markup.add(types.InlineKeyboardButton(category, callback_data=category))

    msg = bot.send_message(chat_id, "Please select a category:", reply_markup=markup)
    user_data[chat_id]["message_ids"].append(msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data in menu.keys())
def show_drink_menu(call):
    chat_id = call.message.chat.id
    category = call.data
    user_data[chat_id]["state"] = "CHOOSING_DRINK"
    user_data[chat_id]["selected_category"] = category

    markup = types.InlineKeyboardMarkup()
    for drink in menu[category]:
        markup.add(types.InlineKeyboardButton(drink, callback_data=drink))

    bot.edit_message_text("Please select a drink:", chat_id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: any(call.data in drinks for drinks in menu.values()))
def handle_drink_selection(call):
    chat_id = call.message.chat.id
    selected_drink = call.data
    user_data[chat_id]["answers"].append(selected_drink)

    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    if user_data[chat_id]["selected_category"] == "Liquor":
        ask_for_mixer(chat_id, selected_drink)
    else:
        ask_quantity(call.message, selected_drink)

def ask_for_mixer(chat_id, selected_drink):
    user_data[chat_id]["state"] = "CHOOSING_MIXER"
    user_data[chat_id]["selected_drink"] = selected_drink

    markup = types.InlineKeyboardMarkup()
    for mixer in menu["Soft Drinks"]:
        markup.add(types.InlineKeyboardButton(mixer, callback_data=f"mixer_{mixer}"))

    msg = bot.send_message(chat_id, "Please select a mixer:", reply_markup=markup)
    user_data[chat_id]["message_ids"].append(msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("mixer_"))
def handle_mixer_selection(call):
    chat_id = call.message.chat.id
    mixer = call.data.split("_")[1]
    selected_drink = user_data[chat_id]["selected_drink"]

    combined_order = f"{selected_drink} with {mixer}"
    user_data[chat_id]["answers"].append(combined_order)

    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    ask_quantity(call.message, combined_order)

def ask_quantity(message, selected_drink):
    chat_id = message.chat.id
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

    except ValueError:
        msg = bot.send_message(chat_id, "Invalid input. Please enter a valid number.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

@bot.callback_query_handler(func=lambda call: call.data in ["yes_more_drinks", "no_more_drinks"])
def handle_more_drinks(call):
    chat_id = call.message.chat.id
    if call.data == "yes_more_drinks":
        show_category_menu(call.message)
    else:
        finalize_order(call.message)

def finalize_order(message):
    chat_id = message.chat.id
    with queue_lock:
        global queue_number
        order_queue_number = queue_number
        queue_number += 1
        save_queue_number(queue_number)

    order_summary = "\n".join(user_data[chat_id]["drink_orders"])
    answers = user_data[chat_id]["answers"]
    caption_text = (
        f"Order Summary:\n{answers[0]}\n{answers[1]}\n{order_summary}\n"
        f"Queue Number: #{order_queue_number}"
    )

    bot.send_message(chat_id, caption_text)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{chat_id}"))

    for admin_id in ADMIN_CHAT_IDS:
        bot.send_message(admin_id, f"New Order:\n{caption_text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    bot.answer_callback_query(call.id)

    try:
        user_chat_id = int(call.data.split("_")[-1])
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

@bot.message_handler(commands=['reset_queue'])
def reset_queue(message):
    if message.chat.id in ADMIN_CHAT_IDS:
        save_queue_number(1)
        bot.send_message(message.chat.id, "Queue number has been reset to 1.")

bot.polling(none_stop=True, interval=0, timeout=20)
