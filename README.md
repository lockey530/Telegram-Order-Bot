# Order Bot

Order Bot is a Telegram bot that allows users to place orders by answering a series of questions and uploading a confirmation of payment. The bot deletes the conversation history and pins the final order details for easy reference. The bot also supports cancelling the order with a simple command.

## Installation

To run the bot, you need to install the following dependencies:

- Python 3.8 or higher
- pyTelegramBotAPI - A simple and easy to use API wrapper for Telegram Bot API
- config - A library for managing configuration files

You also need to create a `config.py` file in the same directory as the bot script and add the following line:

```python
TOKEN = "YOUR_BOT_TOKEN"
replace YOUR_BOT_TOKEN with the token you obtained from BotFather.
```
## Usage
To start the bot, simply run the bot.py script:
```
python bot.py
```
To place an order, send the /start command to the bot and follow the instructions. You will be asked to provide the following information:

- Order description
- Payment type
- Deadline
- Confirmation of payment (picture only)

The bot will then send you a confirmation message with the order details and pin it to the chat. You can view the pinned message at any time by tapping on the pin icon at the top of the chat.

To change the questions, simply replace them in the "questions" list. The last question will always require an image.

To cancel the order, send the /cancel command to the bot. The bot will send you a message that the order was cancelled and pin it to the chat. The previous pinned message will be unpinned.

License

Feel free to use the code for your projects, but do not claim it as your own.
