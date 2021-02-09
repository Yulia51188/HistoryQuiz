import logging
import os
import redis
import vk_api

from dotenv import load_dotenv
from quiz_functions import CORRECT_ANSWER_RESPONSE
from quiz_functions import FAILED_ANSWER_RESPONSE
from quiz_functions import States
from quiz_functions import get_random_question
from quiz_functions import parse_questions
from quiz_functions import validate_answer
from vk_api.keyboard import VkKeyboard
from vk_api.keyboard import VkKeyboardColor
from vk_api.longpoll import VkEventType
from vk_api.longpoll import VkLongPoll
from vk_api.utils import get_random_id

STATE_ID_TEMPLATE = 'vk_{}_state'
QUIZ_ID_TEMPLATE = 'vk_{}_quiz'
SCORE_ID_TEMPLATE = 'vk_{}_score'

logger = logging.getLogger('quiz_bot_logger')


def handle_redis_connection_error(func):

    def run_inner_function(event, vk, *args, **kwargs):
        try:
            return func(event, vk, *args, **kwargs)
        except redis.exceptions.ConnectionError as error:
            logger.error(error)
            vk.messages.send(
                user_id=event.user_id,
                message='Извините, викторина временно недоступна!',
                random_id=get_random_id()
            )

    return run_inner_function


def send_keyboard(event, vk, message, state=States.WAITING_FOR_CLICK):
    keyboard = create_keyboard(state)
    if keyboard:
        vk.messages.send(
            peer_id=event.user_id,
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
            message=message
        )
        return
    vk.messages.send(
        peer_id=event.user_id,
        random_id=get_random_id(),
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
    if state == States.START:
        keyboard = None
    return keyboard


@handle_redis_connection_error
def save_user_state(event, vk, db, new_state):
    db.set(STATE_ID_TEMPLATE.format(event.user_id), new_state.value)
    logger.debug(f'VK user {event.user_id} state {new_state} is saved with key '
        f'{STATE_ID_TEMPLATE.format(event.user_id)}')


@handle_redis_connection_error
def get_user_state(event, vk, db):
    state_value = db.get(STATE_ID_TEMPLATE.format(event.user_id))
    if not state_value:
        return
    state = States(int(state_value))
    logger.debug(f'VK user state {state}={state_value} is got by key '
        f'{STATE_ID_TEMPLATE.format(event.user_id)}')
    return state


def run_bot(token, db_host, db_port, db_password, file_path='test.txt'):
    redis_db = redis.Redis(host=db_host, port=db_port, db=0,
        password=db_password, decode_responses=True)
    quiz = parse_questions(file_path)

    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            state = get_user_state(event, vk, redis_db) or States.START
            logger.debug(f'Current status for {event.user_id} is {state}')
            event_text = event.text.lower().strip()

            if state == States.START:
                state = start_quiz(event, vk)
                save_user_state(event, vk, redis_db, state)
                continue
            if event_text == 'стоп':
                state = stop_quiz(event, vk, redis_db)
            elif event_text == 'новый вопрос' and state == States.WAITING_FOR_CLICK:
                logger.debug('New question button is clicked')
                state = handle_new_question_request(event, vk, redis_db, quiz)
            elif event_text == 'мой счёт' and state == States.WAITING_FOR_CLICK:
                state = handle_my_points_request(event, vk, redis_db)
            elif state == States.WAITING_FOR_CLICK:
                state = handle_unrecognized_button_name(event, vk)
            elif event_text == 'сдаться' and state == States.ANSWER:
                state = handle_give_up_request(event, vk, redis_db, quiz)
            elif state == States.ANSWER:
                state = handle_solution_attempt(event, vk, redis_db, quiz)

            save_user_state(event, vk, redis_db, state)


def start_quiz(event, vk):
    new_state = States.WAITING_FOR_CLICK
    send_keyboard(event, vk, 'Начинаем викторину!', new_state)
    logger.debug(f'Start quiz for {event.user_id}, new state is {new_state}')
    return new_state


def stop_quiz(event, vk, db):
    new_state = States.START
    send_keyboard(event, vk, 'Викторина завершена!', new_state)
    logger.debug(f'Stop quiz for {event.user_id}, new state is {new_state}')
    return new_state


def handle_unrecognized_button_name(event, vk):
    new_state = States.WAITING_FOR_CLICK
    send_keyboard(event, vk, 'Выберите действие', new_state)
    logger.debug(f'Unknown button name from {event.user_id}, new state is {new_state}')
    return new_state


@handle_redis_connection_error
def handle_solution_attempt(event, vk, db, quiz):
    quiz_item = db.get(QUIZ_ID_TEMPLATE.format(event.user_id))
    logger.debug(f"QUIZ ITEM GET:\n{quiz_item}")

    is_answer_true = validate_answer(quiz_item, event.text)
    if is_answer_true:
        old_score = int(db.get(SCORE_ID_TEMPLATE.format(event.user_id)) or 0)
        db.set(SCORE_ID_TEMPLATE.format(event.user_id), old_score + 1)
        logger.debug(f'Add point to {event.user_id}, old is {old_score}')

    bot_message = (is_answer_true and CORRECT_ANSWER_RESPONSE or
        FAILED_ANSWER_RESPONSE)
    new_state = is_answer_true and States.WAITING_FOR_CLICK or States.ANSWER
    send_keyboard(event, vk, bot_message, new_state)
    logger.debug(f'Check answer for {event.user_id}, new state is {new_state}')
    return new_state


@handle_redis_connection_error
def handle_my_points_request(event, vk, db):
    new_state = States.WAITING_FOR_CLICK
    score = db.get(SCORE_ID_TEMPLATE.format(event.user_id))
    send_keyboard(event, vk, f'Набрано баллов: {score}', new_state)
    logger.debug(f'Get score for {event.user_id}, new state is {new_state}')
    return new_state


@handle_redis_connection_error
def handle_give_up_request(event, vk, db, quiz):
    quiz_item = db.get(QUIZ_ID_TEMPLATE.format(event.user_id))
    vk.messages.send(
        user_id=event.user_id,
        message=f'Правильный ответ: {quiz_item}\nДавай попробуем еще!',
        random_id=get_random_id(),
    )
    logger.debug(f'Send give up request for {event.user_id}')
    return handle_new_question_request(event, vk, db, quiz)


@handle_redis_connection_error
def handle_new_question_request(event, vk, db, quiz):
    new_question = get_random_question(quiz)
    new_state = States.ANSWER
    db_item_id = QUIZ_ID_TEMPLATE.format(event.user_id)
    db.set(db_item_id, new_question["answer"])
    send_keyboard(event, vk, new_question["question"], new_state)
    logger.info(f"{db_item_id}: ANSWER:\n{db.get(db_item_id)}")
    return new_state


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    load_dotenv()
    bot_token = os.getenv("VK_TOKEN")
    db_host = os.getenv("DB_HOST", default='localhost')
    db_port = os.getenv("DB_PORT", default=6379)
    db_password = os.getenv("DB_PASSWORD", default=None)
    run_bot(bot_token, db_host, db_port, db_password)


if __name__ == "__main__":
    main()
