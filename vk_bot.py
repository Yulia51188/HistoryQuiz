import logging
import os
import redis
import vk_api

from dotenv import load_dotenv
from quiz_functions import FALSE_RESPONSE
from quiz_functions import States
from quiz_functions import TRUE_RESPONSE
from quiz_functions import get_random_question
from quiz_functions import parse_questions
from quiz_functions import validate_answer
from vk_api.keyboard import VkKeyboard
from vk_api.keyboard import VkKeyboardColor
from vk_api.longpoll import VkEventType
from vk_api.longpoll import VkLongPoll
from vk_api.utils import get_random_id


logger = logging.getLogger('quiz_bot_logger')


def send_keyboard(event, vk, message, state=States.WAITING_FOR_CLICK):
    keyboard = create_keyboard(state)
    vk.messages.send(
        peer_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=message
    )


def create_keyboard(state):
    keyboard = VkKeyboard(one_time=True)
    if state == States.ANSWER:
        keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    elif state == States.WAITING_FOR_CLICK:
        keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)        
        keyboard.add_button('Сдаться', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    return keyboard


def run_bot(token, db_host, db_port, db_password, file_path='test.txt'):
    redis_db = redis.Redis(host=db_host, port=db_port, db=0, 
        password=db_password, decode_responses=True)
    quiz = parse_questions(file_path)

    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    state = States.START
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if state == States.START:
                state = start_quiz(event, vk)
            if event.text == 'Новый вопрос' and state == States.WAITING_FOR_CLICK:
                state = handle_new_question_request(event, vk, redis_db, quiz)
            elif event.text == 'Мой счёт' and state == States.WAITING_FOR_CLICK:
                state = handle_my_points_request(event, vk)
            elif event.text == 'Сдаться' and state == States.ANSWER:
                state = handle_dont_know_request(event, vk, redis_db, quiz)
            elif state == States.ANSWER:
                state = handle_solution_attempt(event, vk, redis_db, quiz)


def start_quiz(event, vk):
    new_state = States.WAITING_FOR_CLICK
    send_keyboard(event, vk, 'Начинаем викторину!', new_state)
    return new_state


def handle_solution_attempt(event, vk, db, quiz):
    quiz_item = db.get(f"vk_{event.user_id}")
    logger.debug(f"QUIZ ITEM GET:\n{quiz_item}")
        
    is_answer_true = validate_answer(quiz_item,  event.text)
    bot_message= is_answer_true and TRUE_RESPONSE or FALSE_RESPONSE
    new_state = is_answer_true and States.WAITING_FOR_CLICK or States.ANSWER    
    send_keyboard(event, vk,  bot_message, new_state)
    return new_state


def handle_my_points_request(event, vk):
    new_state = States.WAITING_FOR_CLICK
    send_keyboard(event, vk, 'Твой счёт 10 баллов', new_state)
    return new_state


def handle_dont_know_request(event, vk, db, quiz):
    quiz_item = db.get(f"vk_{event.user_id}")
    vk.messages.send(
        user_id=event.user_id,
        message=f'Правильный ответ: {quiz_item}\nДавай попробуем еще!',
        random_id=get_random_id()
    )    
    return handle_new_question_request(event, vk, db, quiz)
    

def handle_new_question_request(event, vk, db, quiz):
    new_question = get_random_question(quiz)
    new_state = States.ANSWER
    send_keyboard(event, vk, new_question["question"], new_state)    
    db_item_id = f"vk_{event.user_id}"
    db.set(db_item_id, new_question["answer"])
    logger.info(f"NEW QUIZ ITEM FOR {db_item_id}, ANSWER:\n{db.get(db_item_id)}")
    return new_state


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    load_dotenv()
    bot_token = os.getenv("VK_TOKEN")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_password = os.getenv("DB_PASSWORD")
    run_bot(bot_token, db_host, db_port, db_password)
    

if __name__ == "__main__":
    main()