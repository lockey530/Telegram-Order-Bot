import telebot
import config
from telebot import types
import time

bot = telebot.TeleBot(config.TOKEN)

# Admin chat ID (your user ID)
ADMIN_CHAT_ID = 551429608  # Your actual Telegram user ID

# Drink options
menu = ["Iced Matcha Latte", "Iced Houjicha Latte", "Iced Chocolate"]
questions = ["Please enter your name:", "Please enter your Telegram handle:", "Please choose your drink:", "Payment type (e.g., PayNow, Cash):", "Confirmation of Payment (Picture Only):"]
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
        # If we are at the "Please choose your drink" question, display the drink options
        if questions[question_index] == "Please choose your drink:":
            markup = types.InlineKeyboardMarkup()
            for drink in menu:
                markup.add(types.InlineKeyboardButton(drink, callback_data=drink))
            msg = bot.send_message(message.chat.id, questions[question_index], reply_markup=markup)
            message_ids.append(msg.message_id)
        else:
            msg = bot.send_message(message.chat.id, questions[question_index])
            message_ids.append(msg.message_id)
            bot.register_next_step_handler(msg, handle_answer, message_ids, question_index)
    else:
        # This case should not be hit since we will handle the photo next
        pass

def handle_answer(message, message_ids, question_index):
    answers.append(message.text)  # Save the user's answer
    message_ids.append(message.message_id)  # Save the user's message id
    time.sleep(1)  # Wait for a second before asking the next question to ensure messages are deleted
    ask_question(message, question_index + 1, message_ids)

@bot.callback_query_handler(func=lambda call: True)
def handle_drink_selection(call):
    # The selected drink from the inline buttons
    selected_drink = call.data
    answers.append(selected_drink)  # Save the selected drink
    message_ids = [call.message.message_id]  # Save the message ID
    bot.answer_callback_query(call.id, f"You selected {selected_drink}")
    
    # Continue to the next question after selecting the drink
    ask_question(call.message, 3, message_ids)  # Continue to the next question (payment type)

@bot.message_handler(content_types=['photo'])
def handle_picture(message):
    global last_pinned_message
    # After the user uploads the payment confirmation picture
    if message.content_type == 'photo':
        # Join the questions and answers into a single text
        caption_text = "\n".join(f"{q} {a}" for q, a in zip(questions, answers))
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

@bot.message_handler(commands=['cancel'])
def cancel(message):
    global last_pinned_message
    # Send a message that the order was cancelled
    msg = bot.send_message(message.chat.id, "The order was cancelled.")
    # Pin the message
    bot.pin_chat_message(message.chat.id, msg.message_id)
    last_pinned_message = msg.message_id  # Update the last pinned message

bot.polling(none_stop=True)
