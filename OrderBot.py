import telebot
import config
import time
from telebot import types

bot = telebot.TeleBot(config.TOKEN)

# Admin chat ID (your user ID)
ADMIN_CHAT_ID = 551429608  # Your actual Telegram user ID

# New menu of drink options
menu = ["Iced Matcha Latte", "Iced Houjicha Latte", "Iced Chocolate"]
questions = ["Please enter your name:", "Please enter your Telegram handle:"]
answers = []
drink_orders = []
last_pinned_message = None
order_to_user_map = {}  # To map the admin button press to the user who made the order

@bot.message_handler(commands=['start'])
def welcome(message):
    global last_pinned_message
    last_pinned_message = None  # reset the last pinned message
    answers.clear()  # clear the previous saved messages
    drink_orders.clear()  # clear previous drink orders
    
    # Send the welcome message with drink prices
    welcome_text = ("Hello! Welcome to the Battambar Order Bot. We are selling Iced Matcha, Iced Chocolate, Iced Houjicha Latte. "
                    "Each cup is 4 dollars, and there is 1 dollar off for every 3 drinks.")
    msg = bot.send_message(message.chat.id, welcome_text)
    
    ask_question(message, 0, [msg.message_id])  # Ask for the user's name

def ask_question(message, question_index, message_ids):
    if question_index < len(questions):
        msg = bot.send_message(message.chat.id, questions[question_index])
        message_ids.append(msg.message_id)
        bot.register_next_step_handler(msg, handle_answer, message_ids, question_index)
    elif question_index == len(questions):  # Once name and handle are collected, show the drink menu with inline buttons
        show_menu(message, message_ids)

def handle_answer(message, message_ids, question_index):
    answers.append(message.text)  # save the user's answer
    message_ids.append(message.message_id)  # save the user's message id
    ask_question(message, question_index + 1, message_ids)

def show_menu(message, message_ids):
    # Create inline buttons for drink options
    markup = types.InlineKeyboardMarkup()
    for i, drink in enumerate(menu):
        markup.add(types.InlineKeyboardButton(drink, callback_data=drink))

    msg = bot.send_message(message.chat.id, "Please select a drink:", reply_markup=markup)
    message_ids.append(msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data in menu)
def handle_menu_selection(call):
    selected_drink = call.data
    # Save the selected drink temporarily
    answers.append(selected_drink)
    
    # Ask for the quantity of the selected drink
    msg = bot.send_message(call.message.chat.id, f"How many {selected_drink} would you like?")
    bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink, [call.message.message_id])

def handle_quantity_selection(message, selected_drink, message_ids):
    try:
        quantity = int(message.text)
        if quantity < 1:
            raise ValueError  # invalid input for quantity
        # Save the drink and quantity
        drink_orders.append(f"{quantity} x {selected_drink}")
        message_ids.append(message.message_id)  # save the user's message id

        # Ask if they want to order more drinks
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Yes", callback_data="yes_more_drinks"))
        markup.add(types.InlineKeyboardButton("No", callback_data="no_more_drinks"))

        msg = bot.send_message(message.chat.id, "Would you like to order more drinks?", reply_markup=markup)
        message_ids.append(msg.message_id)

    except ValueError:
        msg = bot.send_message(message.chat.id, "Invalid input. Please enter a valid number for the quantity.")
        bot.register_next_step_handler(msg, handle_quantity_selection, selected_drink, message_ids)

@bot.callback_query_handler(func=lambda call: call.data in ["yes_more_drinks", "no_more_drinks"])
def handle_more_drinks(call):
    if call.data == "yes_more_drinks":
        # Go back to the drink selection to allow more orders
        show_menu(call.message, [call.message.message_id])
    else:
        # Proceed to payment if no more drinks are needed
        msg = bot.send_message(call.message.chat.id, "Please PayNow and upload the payment confirmation photo.")
        bot.register_next_step_handler(msg, handle_payment_confirmation, [call.message.message_id])

def handle_payment_confirmation(message, message_ids):
    if message.content_type == 'photo':  # If the user uploads a photo
        answers.append("Payment confirmation received.")  # Acknowledge photo confirmation
        handle_picture(message, message_ids)
    else:
        msg = bot.send_message(message.chat.id, "Please upload a photo for payment confirmation.")
        bot.register_next_step_handler(msg, handle_payment_confirmation, message_ids)

def handle_picture(message, message_ids):
    global last_pinned_message
    if message.content_type == 'photo':
        # Join the questions and answers into a single text
        order_summary = "\n".join(drink_orders)  # Summarize all drinks and quantities
        caption_text = "\n".join(f"{q} {a}" for q, a in zip(questions, answers)) + f"\n\nDrinks Ordered:\n{order_summary}"
        # Get the photo id
        photo_id = message.photo[-1].file_id
        # Send the photo back to the user with the caption (Order Summary)
        msg = bot.send_photo(message.chat.id, photo_id, caption=f"Order Summary:\n{caption_text}")
        
        # Send the same photo and caption to the admin (your chat) with a "Mark as Ready" button
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Mark as Ready", callback_data=f"order_ready_{message.chat.id}"))  # Store the user's chat ID in the callback
        
        admin_msg = bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"New Order Received:\n{caption_text}", reply_markup=markup)

        # Map the admin's "Mark as Ready" button to the user's chat ID
        order_to_user_map[admin_msg.message_id] = message.chat.id
        
        # Pin the message in the user's chat
        bot.pin_chat_message(message.chat.id, msg.message_id)
        last_pinned_message = msg.message_id  # Update the last pinned message
        
        # Delete the original picture sent by the user
        bot.delete_message(message.chat.id, message.message_id)
        
    # Delete the entire conversation starting at '/start'
    for msg_id in message_ids:
        bot.delete_message(message.chat.id, msg_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_ready_"))
def mark_order_as_ready(call):
    # Extract the user chat ID from the callback data
    user_chat_id = int(call.data.split("_")[-1])
    
    # Send a message to the user that their order is ready
    bot.send_message(user_chat_id, "Your order is ready for collection!")
    
    # Notify the admin that the user has been informed
    bot.send_message(call.message.chat.id, "The user has been informed that their order is ready.")

@bot.message_handler(commands=['cancel'])
def cancel(message):
    global last_pinned_message
    # Send a message that the order was cancelled
    msg = bot.send_message(message.chat.id, "The order was cancelled.")
    # Pin the message
    bot.pin_chat_message(message.chat.id, msg.message_id)
    last_pinned_message = msg.message_id  # Update the last pinned message

bot.polling(none_stop=True)
