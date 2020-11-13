import logging
import os
import random
import vk_api

from dotenv import load_dotenv
from enum import Enum
from vk_api.longpoll import VkEventType
from vk_api.longpoll import VkLongPoll


class States(Enum):
    MENU_BUTTON_CLICK = 1
    ANSWER = 2


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger('quiz_bot_logger')

TRUE_RESPONSE = "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»"
FALSE_RESPONSE = "Неправильно... Попробуешь ещё раз?"


def echo(event, vk_api):
    vk_api.messages.send(
        user_id=event.user_id,
        message=event.text,
        random_id=random.randint(1,1000)
    )

def run_bot(token):
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            echo(event, vk)


def main():
    load_dotenv()
    bot_token = os.getenv("VK_TOKEN")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_password = os.getenv("DB_PASSWORD")
    run_bot(bot_token)
    

if __name__ == "__main__":
    main()