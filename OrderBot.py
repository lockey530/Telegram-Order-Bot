import telebot
import config
import time
import os
from telebot import types

bot = telebot.TeleBot(config.TOKEN)

# Admin chat ID (your user ID)
ADMIN_CHAT_ID = 551429608  # Your actual Telegram user ID

# New menu of drink options
menu = ["Iced Matcha Latte", "Iced Houjicha Latte", "Iced Chocolate", "Surprise Drink"]

# Store each user's order and state
user_data = {}

# File ID for the menu image
MENU_IMAGE_FILE_ID = 'AgACAgUAAxkBAAID3GcPGWk99TJab_qnKizpnIrVjrtZAAIFvzEbnQZ5VP7M3JiITBziAQADAgADeQADNgQ'

# Load the last queue number from the file or initialize it to 1
def load_queue_number():
    try:
        if os.path.exists('queue_counter.txt'):
            with open('queue_counter.txt', 'r') as file:
                return int(file.read().strip())
        else:
            return 1  # Start from 1 if the file doesn't exist
    except Exception as e:
        print(f"Error loading queue number: {e}")
        return 1  # Safe fallback to 1

# Save the current queue number to the file
def save_queue_number(queue_number):
    try:
        with open('queue_counter.txt', 'w') as file:
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
                    "Iced Chocolate, Iced Houjicha Latte, and a Surprise Drink. Each cup is 4 dollars, "
                    "and there is 1 dollar off for every 3 drinks. Our surprise drink is 5 dollars ;)")
    
    # Send the welcome message and menu image
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
    elif question_index == len(questions):
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
        
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, 
                                      message_id=call.message.message_id, 
                                      reply_markup=None)

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
        user_data[chat_id]["message_ids"].append(message.message_id)

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

@bot.callback_query_handler(func=lambda call: call.data == "no_more_drinks")
def finalize_order(call):
    chat_id = call.message.chat.id
    global queue_number

    order_queue_number = queue_number
    queue_number += 1  # Increment the counter for the next order
    save_queue_number(queue_number)  # Save the updated number

    msg = bot.send_message(chat_id, f"Please PayNow +6592331010 and upload the payment confirmation. "
                                    f"Your queue number is #{order_queue_number}.")
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

    msg = bot.send_photo(chat_id, photo_id, caption=caption_text)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{chat_id}"))

    bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"New Order:\n{caption_text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    user_chat_id = int(call.data.split("_")[-1])
    bot.send_message(user_chat_id, "Your order is ready for collection!")
    del user_data[user_chat_id]

bot.polling(none_stop=True)
