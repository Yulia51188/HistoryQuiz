questions_file = 'questions/test.txt'

with open(questions_file, 'r', encoding='koi8-r') as file_obj:
    questions_text = file_obj.read()

text_parts = questions_text.split('\n\n')
questions = [part.split('\n')[1] for part in text_parts 
    if 'Вопрос' in part.split('\n')[0]]
answers = [part.split('\n')[1] for part in text_parts 
    if 'Ответ' in part.split('\n')[0]]   

quiz = [{'question': question, 'answer': answer} 
    for question, answer in zip(questions, answers)]

print(len(quiz))   