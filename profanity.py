import requests
import os

PROFANITY_FILE = 'badwords.txt'
PROFANITY_URL = "https://raw.githubusercontent.com/censor-text/profanity-list/refs/heads/main/list/en.txt"
from openai import OpenAI
#from dotenv import load_dotenv
import os

#load_dotenv("secrets.env")

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

def filter_complete(message: str, client, gpt_version) -> str:

    off_topic = ""
    while not off_topic.lower().startswith("yes") and (not off_topic.lower().startswith("no")):
        off_topic = client.chat.completions.create(model=gpt_version, messages=[{"role": "user", "content": message + "Is this message somehow (even in the broadest sense) related to conspiracy theories? Please only answer with one word: either 'Yes' or 'No'."}]).choices[0].message.content
        print(off_topic)
    if off_topic.lower().startswith("yes"):
        return filter_profanity(message)
    else:
        return "This user tried to send a message which is unrelated to conspiracy theories."
