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

import re

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

TRUE_RESPONSE = "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»"
FALSE_RESPONSE = "Неправильно... Попробуешь ещё раз?"

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    send_keyboard(bot, update.message.chat_id, 'Начинаем викторину!')


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


def validate_answer(full_answer, user_msg):
    if user_msg.lower() == full_answer.lower():
        return True
    elif len(user_msg) < 1:
        return
    else:
        clean_answer = re.sub('[."\n]', '', full_answer.lower())
        logger.debug(clean_answer)
        answer = re.sub(" \([^)]*\)", '', clean_answer)
        answer = re.sub(" \[[^)]*\]", '', answer)
        user_answer = user_msg.replace('.', '').lower()
        logger.info(f"{answer} == {user_answer}")
        return answer == user_answer


def answer(bot, update, db):
    if update.message.text == 'Новый вопрос':
        new_question = get_random_question()
        bot_response = new_question["question"]
        db.set(
            update.message.chat_id, 
            new_question["answer"]
        )
        logger.info(f"QUIZ ITEM SET:\n{db.get(update.message.chat_id)}")

    elif update.message.text == 'Сдаться':
        bot_response = 'Жаль'
        pass
    elif update.message.text == 'Мой счёт':
        bot_response = 'Твой счёт 0'
        pass
    else:
        quiz_item = db.get(update.message.chat_id)
        logger.info(f"QUIZ ITEM GET:\n{quiz_item}")
        
        is_answer_true = validate_answer(quiz_item,  update.message.text)
        bot_response = is_answer_true and TRUE_RESPONSE or FALSE_RESPONSE
        
        # update.message.reply_text(bot_response)
    send_keyboard(bot, update.message.chat_id, bot_response)


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


def send_keyboard(bot, chat_id, text):
    custom_keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счёт']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    bot.send_message(chat_id=chat_id, text=text, 
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
    # print(validate_answer("Голубь и овца (агнец).", "голубь и овца"))



if __name__ == '__main__':
    main()