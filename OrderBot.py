import telebot
import config
import time

bot = telebot.TeleBot(config.TOKEN)

# Admin chat ID (your user ID)
ADMIN_CHAT_ID = 551429608  # Your actual Telegram user ID

# New menu of drink options
menu = ["Iced Matcha Latte", "Iced Houjicha Latte", "Iced Chocolate"]
questions = ["Please enter your name:", "Please enter your Telegram handle:", "Please choose your drink:"]
answers = []
last_pinned_message = None

@bot.message_handler(commands=['start'])
def welcome(message):
    global last_pinned_message
    last_pinned_message = None  # reset the last pinned message
    answers.clear()  # clear the previous saved messages
    ask_question(message, 0, [message.message_id])  # start by asking the user's name

def ask_question(message, question_index, message_ids):
    if question_index < len(questions):
        msg = bot.send_message(message.chat.id, questions[question_index])
        message_ids.append(msg.message_id)
        bot.register_next_step_handler(msg, handle_answer, message_ids, question_index)
    elif question_index == len(questions):  # Handle drink selection step
        show_menu(message, message_ids)

def handle_answer(message, message_ids, question_index):
    answers.append(message.text)  # save the user's answer
    message_ids.append(message.message_id)  # save the user's message id
    ask_question(message, question_index + 1, message_ids)

def show_menu(message, message_ids):
    menu_text = "Please select a drink:\n" + "\n".join(f"{i+1}. {drink}" for i, drink in enumerate(menu))
    msg = bot.send_message(message.chat.id, menu_text)
    message_ids.append(msg.message_id)  # save the bot's message id
    bot.register_next_step_handler(msg, handle_menu_selection, message_ids)

def handle_menu_selection(message, message_ids):
    try:
        choice = int(message.text) - 1
        if choice < 0 or choice >= len(menu):
            raise ValueError  # invalid input, will be handled below
        answers.append(menu[choice])  # save the selected drink
        message_ids.append(message.message_id)  # save the user's message id
        
        # After choosing the drink, instruct them to PayNow and upload a photo
        msg = bot.send_message(message.chat.id, "Please PayNow and upload the payment confirmation photo.")
        message_ids.append(msg.message_id)
        bot.register_next_step_handler(msg, handle_payment_confirmation, message_ids)
    except (ValueError, IndexError):
        msg = bot.send_message(message.chat.id, "Invalid choice. Please select a valid drink option (1, 2, or 3).")
        message_ids.append(msg.message_id)  # save the invalid input message
        bot.register_next_step_handler(msg, handle_menu_selection, message_ids)

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
        caption_text = "\n".join(f"{q} {a}" for q, a in zip(questions + ["Payment method"], answers))
        # Get the photo id
        photo_id = message.photo[-1].file_id
        # Send the photo back to the user with the caption (Order Summary)
        msg = bot.send_photo(message.chat.id, photo_id, caption=f"Order Summary:\n{caption_text}")
        
        # Send the same photo and caption to the admin (your chat)
        bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"New Order Received:\n{caption_text}")
        
        # Pin the message in the user's chat
        bot.pin_chat_message(message.chat.id, msg.message_id)
        last_pinned_message = msg.message_id  # Update the last pinned message
        
        # Delete the original picture sent by the user
        bot.delete_message(message.chat.id, message.message_id)
        
    # Delete the entire conversation starting at '/start'
    for msg_id in message_ids:
        bot.delete_message(message.chat.id, msg_id)

@bot.message_handler(commands=['cancel'])
def cancel(message):
    global last_pinned_message
    # Send a message that the order was cancelled
    msg = bot.send_message(message.chat.id, "The order was cancelled.")
    # Pin the message
    bot.pin_chat_message(message.chat.id, msg.message_id)
    last_pinned_message = msg.message_id  # Update the last pinned message

bot.polling(none_stop=True)
