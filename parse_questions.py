import logging
import random
import re

from enum import Enum

logger = logging.getLogger('quiz_bot_logger')


TRUE_RESPONSE = "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»"
FALSE_RESPONSE = "Неправильно... Попробуешь ещё раз?"


class States(Enum):
    START = 0
    WAITING_FOR_CLICK = 1
    ANSWER = 2


def get_random_question(quiz):   
    question = random.choice(quiz)
    logger.info(question)
    return(question)


def parse_questions(file_path):
    with open(file_path, 'r', encoding='koi8-r') as file_obj:
        questions_text = file_obj.read()

    text_parts = questions_text.split('Вопрос')
    quiz = []
    for part in text_parts[1:]:
        subparts = part.split('\n\n')
        if len(subparts) > 1:
            quiz.append({
                'question': subparts[0].split(':\n')[1],
                'answer': subparts[1].split(':\n')[1],
            })

    for part in quiz:
        logger.debug(f'Вопрос: {part["question"]}')
        logger.debug(f'Ответ: {part["answer"]}')        
        logger.debug('')
    logger.info(f"Parsed {len(quiz)} questions") 
    return quiz


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


def main():
    logging.basicConfig(format='%(message)s',
                    level=logging.INFO)
    questions_file = 'test.txt'
    parse_questions(questions_file)


if __name__ == '__main__':
    main()