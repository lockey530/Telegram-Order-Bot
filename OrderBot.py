import telebot
import config

bot = telebot.TeleBot(config.TOKEN)

@bot.message_handler(content_types=['photo'])
def get_photo_id(message):
    # Extract the file ID from the uploaded photo
    file_id = message.photo[-1].file_id
    bot.send_message(message.chat.id, f"File ID: {file_id}")
    print(f"File ID: {file_id}")  # Print it to your console/terminal

# Start polling to receive messages
bot.polling(none_stop=True, interval=0, timeout=20)
