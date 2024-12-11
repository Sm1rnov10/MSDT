import re


def remove_extra_spaces(text):
    """удаляет лишние пробелы из текста"""
    return re.sub(r'\s+', ' ', text.strip())


def add_spaces_after_punctuation(text):
    """добавляет пробелы после точек, запятых и других знаков препинания"""
    return re.sub(r'(\.|,|!|\?)\s*', r'\1 ', text).strip()


def fix_ellipsis(text):
    """исправляет многоточия, приводя их к стандартному виду '...'"""
    return re.sub(r'\.{3,}', '... ', text)


def capitalize_sentences(text):
    """делает первую букву каждого предложения заглавной"""
    sentences = re.split(r'(\.|!|\?)', text)
    processed_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i].strip()
        punctuation = sentences[i + 1]
        processed_sentences.append(sentence.capitalize() + punctuation)
    if len(sentences) % 2 != 0:
        processed_sentences.append(sentences[-1].capitalize())
    return ' '.join(processed_sentences).strip()


def remove_numbers(text):
    """удаляет все цифры из текста"""
    return re.sub(r'\d+', '', text)


def count_words(text):
    """подсчитывает количество слов в тексте"""
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def reverse_text(text):
    """переворачивает текст задом наперед"""
    return text[::-1]


def translit_to_russian(text):
    """преобразует текст, введенный транслитом, в русский язык"""
    translit_map = {
        'a': 'а', 'b': 'б', 'v': 'в', 'g': 'г', 'd': 'д', 'e': 'е', 'yo': 'ё',
        'zh': 'ж', 'z': 'з', 'i': 'и', 'y': 'й', 'k': 'к', 'l': 'л', 'm': 'м',
        'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
        'f': 'ф', 'h': 'х', 'ts': 'ц', 'ch': 'ч', 'sh': 'ш', 'sch': 'щ',
        'yu': 'ю', 'ya': 'я'
    }
    pattern = re.compile('|'.join(map(re.escape, sorted(translit_map.keys(),
                                                        key=len,
                                                        reverse=True))))
    return pattern.sub(lambda x: translit_map[x.group()], text)


def get_user_input():
    """считывает текст, введенный пользователем через консоль"""
    print("Введите текст для обработки:")
    user_input = []
    while True:
        line = input()
        if line == '':
            break
        user_input.append(line)
    return '\n'.join(user_input)
