
import logging

logger = logging.getLogger('quiz_bot_logger')
logging.basicConfig(format='%(message)s',
                    level=logging.DEBUG)

def parse_questions(file_path):
    with open(file_path, 'r', encoding='koi8-r') as file_obj:
        questions_text = file_obj.read()

    text_parts = questions_text.split('Вопрос')
    quiz = []
    for part in text_parts[1:]:
        subparts = part.split('\n\n')
        logger.debug(subparts)
        if len(subparts) > 1:
            quiz.append({
                'question': subparts[0].split(':')[1],
                'answer': subparts[1].split(':')[1],
            })

    for part in quiz:
        logger.debug(f'Вопрос: {part["question"]}')
        logger.debug(f'Ответ: {part["answer"]}')        
        logger.debug('')
    logger.info(f"Parsed {len(quiz)} questions") 
    return quiz


def main():
    questions_file = 'Data/120br.txt'
    parse_questions(questions_file)


if __name__ == '__main__':
    main()