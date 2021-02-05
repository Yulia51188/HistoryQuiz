import logging
import random
import re

from enum import Enum

logger = logging.getLogger('quiz_bot_logger')

CORRECT_ANSWER_RESPONSE = "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»"
FAILED_ANSWER_RESPONSE = "Неправильно... Попробуешь ещё раз?"


class States(Enum):
    START = 0
    WAITING_FOR_CLICK = 1
    ANSWER = 2


def get_random_question(quiz):
    question = random.choice(quiz)
    logger.debug(question)
    return(question)


def parse_questions(file_path):
    with open(file_path, 'r', encoding='koi8-r') as file_obj:
        questions_text = file_obj.read()
    questions = [paragraph.split(':\n')[1]
                for paragraph in questions_text.split("\n\n")
                if 'Вопрос' in paragraph]
    logging.debug(questions[0])
    answers = [paragraph.split(':\n')[1]
                for paragraph in questions_text.split("\n\n")
                if 'Ответ' in paragraph]
    quiz = [{"question": question, "answer": answer}
        for question, answer in zip(questions, answers)]
    for item in quiz:
        logger.debug(f'Вопрос: {item["question"]}')
        logger.debug(f'Ответ: {item["answer"]}')
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
        answer = re.sub(r" \([^)]*\)", '', clean_answer)
        answer = re.sub(r" \[[^)]*\]", '', answer)
        user_answer = user_msg.replace('.', '').lower()
        logger.debug(f"{answer} == {user_answer}")
        return answer == user_answer


def main():
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    parse_questions('test.txt')


if __name__ == '__main__':
    main()