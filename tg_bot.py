#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Simple Bot to reply to Telegram messages.
This program is dedicated to the public domain under the CC0 license.
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os

import random

from dotenv import load_dotenv
from functools import partial
from parse_questions import parse_questions
from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

import redis
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger('quiz_bot_logger')


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')
    send_keyboard(bot, update.message.chat_id)


def stop(bot, update):
    """Send a message when the command /start is issued."""
    remove_keyboard(bot, update.message.chat_id)


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(bot, update):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def answer(bot, update, db):
    if update.message.text == 'Новый вопрос':
        new_question = get_random_question()
        update.message.reply_text(new_question["question"])
        db.set(update.message.chat_id, new_question["question"])
        logger.info(db.get(update.message.chat_id))


def run_echobot(bot_token, db_host, db_port, db_password):
    redis_db = redis.Redis(host=db_host, port=db_port, db=0, 
        password=db_password, decode_responses=True)

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(bot_token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("stop", stop))
    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(
        Filters.text, 
        partial(
                answer, 
                db=redis_db
            )
    ))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def send_keyboard(bot, chat_id):
    custom_keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счёт']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    bot.send_message(chat_id=chat_id, text="Начинаем викторину!", 
        reply_markup=reply_markup)


def remove_keyboard(bot, chat_id):
    reply_markup = ReplyKeyboardRemove()
    bot.send_message(chat_id=chat_id, text='Викторина прервана', 
        reply_markup=reply_markup)


def get_random_question(file_path='Data/test.txt'):
    quiz = parse_questions(file_path)
    question = random.choice(quiz)
    logger.info(question)
    return(question)


def main():
    load_dotenv()
    bot_token = os.getenv("TOKEN")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_password = os.getenv("DB_PASSWORD")
    run_echobot(bot_token, db_host, db_port, db_password)



if __name__ == '__main__':
    main()