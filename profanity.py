import requests
import os

PROFANITY_FILE = 'badwords.txt'
PROFANITY_URL = "https://raw.githubusercontent.com/censor-text/profanity-list/refs/heads/main/list/en.txt"


def filter_profanity(sentence: str) -> str:
    prof = None
    if not os.path.isfile(PROFANITY_FILE):
        url = PROFANITY_URL
        response = requests.get(url)
        prof = response.text
        if response.status_code < 200 or response.status_code >= 300:
            return sentence
        with open(PROFANITY_FILE, 'w') as f:
            f.write(prof)
    else:
        with open(PROFANITY_FILE, 'r') as f:
            prof = f.read()
    bad_words = set(prof.split('\n'))
    for word in sentence.split():
        if word in bad_words:
            sentence = sentence.replace(word, '*' * len(word))
    return sentence
