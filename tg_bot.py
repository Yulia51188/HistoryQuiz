#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import random
import re
import redis

from dotenv import load_dotenv
from enum import Enum
from functools import partial
from parse_questions import parse_questions
from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import RegexHandler
from telegram.ext import Updater


class States(Enum):
    MENU_BUTTON_CLICK = 1
    ANSWER = 2


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger('quiz_bot_logger')

TRUE_RESPONSE = "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»"
FALSE_RESPONSE = "Неправильно... Попробуешь ещё раз?"

# MENU_BUTTON_CLICK, ANSWER = range(2)


def start(bot, update):
    send_keyboard(bot, update.message.chat_id, 'Начинаем викторину!')
    return States.MENU_BUTTON_CLICK


def stop(bot, update):
    remove_keyboard(bot, update.message.chat_id)
    return ConversationHandler.END 


def error(bot, update, error):
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


def handle_new_question_request(bot, update, db):
    new_question = get_random_question()
    bot_response = new_question["question"]
    send_keyboard(bot, update.message.chat_id, bot_response)    
    db.set(
        update.message.chat_id, 
        new_question["answer"]
    )
    logger.info(f"QUIZ ITEM SET:\n{db.get(update.message.chat_id)}")
    return States.ANSWER


def handle_solution_attempt(bot, update, db):
    quiz_item = db.get(update.message.chat_id)
    logger.info(f"QUIZ ITEM GET:\n{quiz_item}")
        
    is_answer_true = validate_answer(quiz_item,  update.message.text)
    bot_response = is_answer_true and TRUE_RESPONSE or FALSE_RESPONSE
        
    send_keyboard(bot, update.message.chat_id, bot_response)
    return is_answer_true and States.MENU_BUTTON_CLICK or States.ANSWER


def handle_my_points_request(bot, update):
    send_keyboard(bot, update.message.chat_id, 'Твой счёт 10 баллов')
    return States.MENU_BUTTON_CLICK


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


def run_bot(bot_token, db_host, db_port, db_password):
    redis_db = redis.Redis(host=db_host, port=db_port, db=0, 
        password=db_password, decode_responses=True)

    updater = Updater(bot_token)
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            States.MENU_BUTTON_CLICK: [
                RegexHandler('^Новый вопрос$', 
                    partial(handle_new_question_request, db=redis_db)),
                RegexHandler('^Мой счёт$', 
                    handle_my_points_request),
                ],
            States.ANSWER: [MessageHandler(
                Filters.text, 
                partial(handle_solution_attempt, db=redis_db)
            )],
        },
        fallbacks=[CommandHandler('stop', stop)]
    )
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    updater.idle()


def main():
    load_dotenv()
    bot_token = os.getenv("TOKEN")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_password = os.getenv("DB_PASSWORD")
    run_bot(bot_token, db_host, db_port, db_password)


if __name__ == '__main__':
    main()