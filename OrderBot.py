import telebot
import config
import os
from telebot import types

bot = telebot.TeleBot(config.TOKEN)

# Admin chat ID (your user ID)
ADMIN_CHAT_ID = 551429608

# Menu options
menu = ["Iced Matcha Latte", "Iced Houjicha Latte", "Iced Chocolate", "Surprise Drink"]

# Store user-specific data
user_data = {}

# File ID for the menu image
MENU_IMAGE_FILE_ID = 'AgACAgUAAxkBAAID3GcPGWk99TJab_qnKizpnIrVjrtZAAIFvzEbnQZ5VP7M3JiITBziAQADAgADeQADNgQ'

# Queue counter file
QUEUE_FILE = "queue_counter.txt"

# Load the queue number from the file or initialize it
def load_queue_number():
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as file:
                return int(file.read().strip())
        else:
            return 1  # Initialize to 1 if no file exists
    except Exception as e:
        print(f"Error loading queue number: {e}")
        return 1  # Safe fallback

# Save the updated queue number to the file
def save_queue_number(queue_number):
    try:
        with open(QUEUE_FILE, 'w') as file:
            file.write(str(queue_number))
    except Exception as e:
        print(f"Error saving queue number: {e}")

# Initialize the global queue number
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
    selected_drink = call.data

    user_data[chat_id]["answers"].append(selected_drink)

    msg = bot.send_message(chat_id, f"How many {selected_drink} would you like?")
    user_data[chat_id]["message_ids"].append(msg.message_id)
    bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

def handle_quantity_selection(message, selected_drink):
    chat_id = message.chat.id
    try:
        quantity = int(message.text)
        if quantity < 1:
            raise ValueError

        user_data[chat_id]["drink_orders"].append(f"{quantity} x {selected_drink}")

        # Ask for payment
        msg = bot.send_message(
            chat_id,
            "Please PayNow Reiyean +6592331010 and upload the payment confirmation photo.\n\n"
            "Support our scholarship program for underprivileged children—feel free to contribute more than "
            "the required amount and make a difference today!"
        )
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_payment_confirmation)

    except ValueError:
        msg = bot.send_message(chat_id, "Please enter a valid quantity.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

def handle_payment_confirmation(message):
    chat_id = message.chat.id
    if message.content_type == 'photo':
        # Assign the queue number only after payment confirmation
        global queue_number
        order_queue_number = queue_number
        queue_number += 1
        save_queue_number(queue_number)

        user_data[chat_id]["answers"].append(f"Queue Number: #{order_queue_number}")
        handle_picture(message, order_queue_number)
    else:
        msg = bot.send_message(chat_id, "Please upload a photo for payment confirmation.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_payment_confirmation)

def handle_picture(message, order_queue_number):
    chat_id = message.chat.id
    photo_id = message.photo[-1].file_id

    order_summary = "\n".join(user_data[chat_id]["drink_orders"])
    answers = "\n".join(user_data[chat_id]["answers"])
    caption_text = f"{answers}\n\nDrinks Ordered:\n{order_summary}\nQueue Number: #{order_queue_number}"

    bot.send_photo(chat_id, photo_id, caption=f"Order Summary:\n{caption_text}")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{chat_id}"))

    bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"New Order:\n{caption_text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    user_chat_id = int(call.data.split("_")[-1])
    bot.send_message(user_chat_id, "Your order is ready for collection!")
    del user_data[user_chat_id]

@bot.message_handler(commands=['cancel'])
def cancel(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "The order was cancelled.")
    bot.pin_chat_message(chat_id, msg.message_id)

@bot.message_handler(commands=['reset_queue'])
def reset_queue(message):
    chat_id = message.chat.id
    if chat_id == ADMIN_CHAT_ID:  # Ensure only the admin can reset the queue
        try:
            with open(QUEUE_FILE, 'w') as file:
                file.write('1')  # Reset the queue number to 1
            bot.send_message(chat_id, "Queue number has been reset to 1.")
        except Exception as e:
            bot.send_message(chat_id, f"Failed to reset queue: {e}")
    else:
        bot.send_message(chat_id, "You are not authorized to reset the queue.")

bot.polling(none_stop=True)
