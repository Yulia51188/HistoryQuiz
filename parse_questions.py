
import logging

logger = logging.getLogger('quiz_bot_logger')

def parse_questions(file_path):
    with open(file_path, 'r', encoding='koi8-r') as file_obj:
        questions_text = file_obj.read()

    text_parts = questions_text.split('\n\n')
    questions = [part.split('\n')[1] for part in text_parts 
        if 'Вопрос' in part.split('\n')[0]]
    answers = [part.split('\n')[1] for part in text_parts 
        if 'Ответ' in part.split('\n')[0]]   

    quiz = [{'question': question, 'answer': answer} 
        for question, answer in zip(questions, answers)]

    logger.info(f"Parsed {len(quiz)} questions") 
    return quiz


def main():
    questions_file = 'questions/test.txt'
    parse_questions(questions_file)


if __name__ == '__main__':
    main()