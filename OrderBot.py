import telebot
import config
import os
from telebot import types

bot = telebot.TeleBot(config.TOKEN)

# Admin chat ID (your user ID)
ADMIN_CHAT_ID = 551429608  # Replace with your actual Telegram user ID

# Menu options
menu = ["Iced Matcha Latte", "Iced Houjicha Latte", "Iced Chocolate", "Surprise Drink"]

# Store user data
user_data = {}

# File ID for the menu image
MENU_IMAGE_FILE_ID = 'AgACAgUAAxkBAAID3GcPGWk99TJab_qnKizpnIrVjrtZAAIFvzEbnQZ5VP7M3JiITBziAQADAgADeQADNgQ'

# Initialize the counter
QUEUE_FILE = "queue_counter.txt"

def load_queue_number():
    """Load the queue number from a file."""
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as file:
                return int(file.read().strip())
        else:
            return 1  # Initialize to 1 if no file exists
    except Exception as e:
        print(f"Error loading queue number: {e}")
        return 1  # Safe fallback

def save_queue_number(queue_number):
    """Save the queue number to a file."""
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
    user_data[chat_id] = {"answers": [], "drink_orders": [], "message_ids": [], 
                          "username": message.from_user.username, "state": "START"}

    welcome_text = ("Hello! Welcome to the Battambar Order Bot. We are selling Iced Matcha, "
                    "Iced Chocolate, Iced Houjicha Latte, and a Surprise Drink. "
                    "Each cup is 4 dollars, with 1 dollar off for every 3 drinks. "
                    "The surprise drink is 5 dollars.")

    # Send welcome message and menu image
    msg = bot.send_message(chat_id, welcome_text)
    user_data[chat_id]["message_ids"].append(msg.message_id)

    menu_msg = bot.send_photo(chat_id, MENU_IMAGE_FILE_ID)
    user_data[chat_id]["message_ids"].append(menu_msg.message_id)

    # Ask for the user's name
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

    # Save the selected drink
    user_data[chat_id]["answers"].append(selected_drink)

    # Ask for quantity
    msg = bot.send_message(chat_id, f"How many {selected_drink} would you like?")
    user_data[chat_id]["message_ids"].append(msg.message_id)
    bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

def handle_quantity_selection(message, selected_drink):
    chat_id = message.chat.id
    try:
        quantity = int(message.text)
        if quantity < 1:
            raise ValueError

        # Save the drink order
        user_data[chat_id]["drink_orders"].append(f"{quantity} x {selected_drink}")

        # Proceed to payment
        finalize_order(chat_id)

    except ValueError:
        msg = bot.send_message(chat_id, "Please enter a valid quantity.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

def finalize_order(chat_id):
    global queue_number

    # Assign and increment the queue number
    order_queue_number = queue_number
    queue_number += 1
    save_queue_number(queue_number)  # Save the updated number

    # Send payment instructions
    msg = bot.send_message(
        chat_id,
        f"Your queue number is #{order_queue_number}. Please PayNow +6592331010 and "
        "upload the payment confirmation."
    )
    user_data[chat_id]["message_ids"].append(msg.message_id)
    bot.register_next_step_handler(msg, handle_payment_confirmation)

def handle_payment_confirmation(message):
    chat_id = message.chat.id
    if message.content_type == 'photo':
        handle_picture(message)
    else:
        msg = bot.send_message(chat_id, "Please upload a photo of your payment confirmation.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_payment_confirmation)

def handle_picture(message):
    chat_id = message.chat.id
    photo_id = message.photo[-1].file_id

    order_summary = "\n".join(user_data[chat_id]["drink_orders"])
    caption_text = f"Order Summary:\n{order_summary}"

    # Send order summary back to the user
    bot.send_photo(chat_id, photo_id, caption=caption_text)

    # Send to admin with "Mark as Ready" button
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{chat_id}"))

    bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"New Order:\n{caption_text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    user_chat_id = int(call.data.split("_")[-1])
    bot.send_message(user_chat_id, "Your order is ready for collection!")
    del user_data[user_chat_id]  # Clear user data

bot.polling(none_stop=True)
