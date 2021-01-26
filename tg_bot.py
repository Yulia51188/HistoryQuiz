import logging
import os
import redis

from dotenv import load_dotenv
from functools import partial
from quiz_functions import CORRECT_ANSWER_RESPONSE
from quiz_functions import FAILED_ANSWER_RESPONSE
from quiz_functions import States
from quiz_functions import get_random_question
from quiz_functions import parse_questions
from quiz_functions import validate_answer
from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import RegexHandler
from telegram.ext import Updater

logger = logging.getLogger('quiz_bot_logger') 


def start(bot, update):
    send_message_with_keyboard(bot, update.message.chat_id, 'Начинаем викторину!')
    return States.WAITING_FOR_CLICK


def stop(bot, update):
    remove_keyboard(bot, update.message.chat_id)
    return ConversationHandler.END 


def handle_error(bot, update, error):
    logger.error('Update "%s" caused error "%s"', update, error)


def handle_new_question_request(bot, update, db, quiz):
    new_question = get_random_question(quiz)
    send_message_with_keyboard(bot, update.message.chat_id, 
        new_question["question"])    
    db_item_id = f"tg_{update.message.chat_id}"
    db.set(db_item_id, new_question["answer"])
    logger.info(f"NEW QUIZ ITEM FOR {db_item_id}, ANSWER:\n{db.get(db_item_id)}")
    return States.ANSWER


def handle_solution_attempt(bot, update, db, quiz):
    quiz_item = db.get(f"tg_{update.message.chat_id}")
    logger.debug(f"QUIZ ITEM GET:\n{quiz_item}")
        
    is_answer_true = validate_answer(quiz_item,  update.message.text)
    bot_message = (is_answer_true and CORRECT_ANSWER_RESPONSE or 
        FAILED_ANSWER_RESPONSE)
        
    send_message_with_keyboard(bot, update.message.chat_id, bot_message)
    return is_answer_true and States.WAITING_FOR_CLICK or States.ANSWER


def handle_my_points_request(bot, update):
    #TODO
    send_message_with_keyboard(bot, update.message.chat_id, 'Твой счёт 10 баллов')
    return States.WAITING_FOR_CLICK


def handle_give_up_request(bot, update, db, quiz):
    quiz_item = db.get(f"tg_{update.message.chat_id}")
    bot.send_message(chat_id=update.message.chat_id, 
        text=f'Правильный ответ: {quiz_item}\nДавай попробуем еще!')
    return handle_new_question_request(bot, update, db, quiz)


def send_message_with_keyboard(bot, chat_id, message):
    custom_keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счёт']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    bot.send_message(chat_id=chat_id, text=message, 
        reply_markup=reply_markup)


def remove_keyboard(bot, chat_id):
    reply_markup = ReplyKeyboardRemove()
    bot.send_message(chat_id=chat_id, text='Викторина прервана', 
        reply_markup=reply_markup)


def run_bot(bot_token, db_host, db_port, db_password, file_path='test.txt'):
    redis_db = redis.Redis(host=db_host, port=db_port, db=0, 
        password=db_password, decode_responses=True)
    quiz = parse_questions(file_path)

    updater = Updater(bot_token)
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.WAITING_FOR_CLICK: [
                RegexHandler('^Новый вопрос$', 
                    partial(
                        handle_new_question_request, 
                        db=redis_db, 
                        quiz=quiz
                    )
                ),
                RegexHandler('^Мой счёт$', 
                    handle_my_points_request),
                ],
            States.ANSWER: [
                    RegexHandler('^Сдаться$', 
                        partial(
                            handle_give_up_request, 
                            db=redis_db,
                            quiz=quiz
                        )
                    ),
                    MessageHandler(Filters.text, 
                        partial(
                            handle_solution_attempt,
                            db=redis_db,
                            quiz=quiz
                        )
                    ),
                ],
        },
        fallbacks=[CommandHandler('stop', stop)]
    )
    dp.add_handler(conv_handler)
    dp.add_error_handler(handle_error)

    updater.start_polling()
    updater.idle()


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )   
    load_dotenv()
    bot_token = os.getenv("TG_TOKEN")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_password = os.getenv("DB_PASSWORD")
    run_bot(bot_token, db_host, db_port, db_password)


if __name__ == '__main__':
    main()