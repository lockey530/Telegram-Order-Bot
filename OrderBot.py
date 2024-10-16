import telebot
import config
import time
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

@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"answers": [], "drink_orders": [], "message_ids": [], "username": message.from_user.username, "state": "START"}  # Initialize user-specific data
    
    welcome_text = ("Hello! Welcome to the Battambar Order Bot. We are selling Iced Matcha, Iced Chocolate, Iced Houjicha Latte, and a Surprise Drink. "
                    "Each cup is 4 dollars, and there is 1 dollar off for every 3 drinks. Our surprise drink is 5 dollars ;)")
    
    # Send the welcome text first
    msg = bot.send_message(chat_id, welcome_text)
    user_data[chat_id]["message_ids"].append(msg.message_id)
    
    # Then send the image menu
    bot.send_photo(chat_id, MENU_IMAGE_FILE_ID)

    # After the menu is sent, ask for the name (first question)
    ask_question(message, 0)

def ask_question(message, question_index):
    chat_id = message.chat.id
    questions = ["Please enter your name:", "Please enter your Telegram handle:"]
    
    if question_index < len(questions):
        msg = bot.send_message(chat_id, questions[question_index])
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_answer, question_index)
    elif question_index == len(questions):  # Once name and handle are collected, show the drink menu with inline buttons
        show_menu(message)

def handle_answer(message, question_index):
    chat_id = message.chat.id
    user_data[chat_id]["answers"].append(message.text)  # Save user's answer
    user_data[chat_id]["message_ids"].append(message.message_id)
    ask_question(message, question_index + 1)

def show_menu(message):
    chat_id = message.chat.id
    user_data[chat_id]["state"] = "CHOOSING_DRINK"  # Set the state to prevent multiple taps
    # Create inline buttons for drink options (including Surprise Drink)
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
        # Save the selected drink
        user_data[chat_id]["answers"].append(selected_drink)
        
        # Disable the inline buttons after a selection
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        
        # Ask for the quantity of the selected drink
        msg = bot.send_message(chat_id, f"How many {selected_drink} would you like?")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        user_data[chat_id]["state"] = "CHOOSING_QUANTITY"
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)
    else:
        bot.send_message(chat_id, "You have already selected a drink. Please proceed.")

def handle_quantity_selection(message, selected_drink):
    chat_id = message.chat.id
    try:
        quantity = int(message.text)
        if quantity < 1:
            raise ValueError  # Invalid input for quantity
        # Save the drink and quantity
        user_data[chat_id]["drink_orders"].append(f"{quantity} x {selected_drink}")
        user_data[chat_id]["message_ids"].append(message.message_id)

        # Ask if they want to order more drinks
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Yes", callback_data="yes_more_drinks"))
        markup.add(types.InlineKeyboardButton("No", callback_data="no_more_drinks"))

        msg = bot.send_message(chat_id, "Would you like to order more drinks?", reply_markup=markup)
        user_data[chat_id]["message_ids"].append(msg.message_id)
        user_data[chat_id]["state"] = "MORE_DRINKS"

    except ValueError:
        msg = bot.send_message(chat_id, "Invalid input. Please enter a valid number for the quantity.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink)

@bot.callback_query_handler(func=lambda call: call.data in ["yes_more_drinks", "no_more_drinks"])
def handle_more_drinks(call):
    chat_id = call.message.chat.id
    if user_data[chat_id]["state"] == "MORE_DRINKS":
        if call.data == "yes_more_drinks":
            # Go back to the drink selection to allow more orders
            show_menu(call.message)
        else:
            # Proceed to payment if no more drinks are needed
            msg = bot.send_message(chat_id, "Please PayNow Reiyean +6592331010 and upload the payment confirmation photo.")
            user_data[chat_id]["message_ids"].append(msg.message_id)
            bot.register_next_step_handler(msg, handle_payment_confirmation)
            user_data[chat_id]["state"] = "AWAITING_PAYMENT"
    else:
        bot.send_message(chat_id, "You've already made a choice. Please continue with the payment.")

def handle_payment_confirmation(message):
    chat_id = message.chat.id
    if message.content_type == 'photo':  # If the user uploads a photo
        user_data[chat_id]["answers"].append("Payment confirmation received.")
        handle_picture(message)
    else:
        msg = bot.send_message(chat_id, "Please upload a photo for payment confirmation.")
        user_data[chat_id]["message_ids"].append(msg.message_id)
        bot.register_next_step_handler(msg, handle_payment_confirmation)

def handle_picture(message):
    chat_id = message.chat.id
    global last_pinned_message
    if message.content_type == 'photo':
        # Summarize the order
        order_summary = "\n".join(user_data[chat_id]["drink_orders"])  # Drinks and quantities
        answers = user_data[chat_id]["answers"]
        caption_text = "\n".join(f"{q}" for q in answers) + f"\n\nDrinks Ordered:\n{order_summary}"
        
        # Get the photo id
        photo_id = message.photo[-1].file_id
        
        # Send the photo back to the user with the caption (Order Summary)
        msg = bot.send_photo(chat_id, photo_id, caption=f"Order Summary:\n{caption_text}")
        
        # Delete all previous messages except the order summary
        for msg_id in user_data[chat_id]["message_ids"]:
            try:
                bot.delete_message(chat_id, msg_id)
            except:
                pass  # Ignore if the message has already been deleted
        
        # Send the same photo and caption to the admin (your chat) with a "Mark as Ready" button
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{chat_id}"))  # Store the user's chat ID in the callback
        
        try:
            admin_msg = bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"New Order Received:\n{caption_text}", reply_markup=markup)
        except Exception as e:
            bot.send_message(ADMIN_CHAT_ID, f"Error sending order: {e}")

        # Pin the message in the user's chat
        bot.pin_chat_message(chat_id, msg.message_id)
        last_pinned_message = msg.message_id  # Update the last pinned message
        
        # Delete the original picture sent by the user
        bot.delete_message(chat_id, message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    user_chat_id = int(call.data.split("_")[-1])
    username = user_data[user_chat_id]["username"]
    
    # Send a message to the user that their order is ready
    bot.send_message(user_chat_id, "Your order is ready for collection!")
    
    # Notify the admin with the username of the user who placed the order
    bot.send_message(call.message.chat.id, f"The user @{username} has been informed that their order is ready.")

    # Clear user data after order is complete
    if user_chat_id in user_data:
        del user_data[user_chat_id]  # This removes the user's data from memory

@bot.message_handler(commands=['cancel'])
def cancel(message):
    chat_id = message.chat.id
    # Send a message that the order was cancelled
    msg = bot.send_message(chat_id, "The order was cancelled.")
    # Pin the message
    bot.pin_chat_message(chat_id, msg.message_id)

bot.polling(none_stop=True)
