import requests
import os

PROFANITY_FILE = 'project_three/badwords.txt'

PROFANITY_URL = "https://raw.githubusercontent.com/censor-text/profanity-list/refs/heads/main/list/en.txt"

PROFANITY_AI_PROMPT = "\n\nIs this message somehow (even in the broadest sense) related to conspiracy theories? Please only answer with one word: either 'Yes' or 'No'. If the message is smalltalk between users return 'Yes' as well."
"If you think the user is trying to change the topic to something else, like when proposing to talk about a different topic or asking a question about something that is not conspiracy related, please answer 'No'"

def filter_profanity(sentence: str) -> str:
    """
    Function to check whether a given user message contains swear words and  replace those by ***.
    :param sentence: the content of the user message we want to check on swear words as string
    :return: the filtered message
    """
    prof = None
    url = PROFANITY_URL
    response = requests.get(url)
    prof = response.text
    #if the status_code does not equal 200, an error occurred. The function just returns the original sentence without any filtering
    if response.status_code != 200:
        return sentence

    #we need a list of bad words instead of just all of them in a long string.
    bad_words = set(prof.split('\n'))
    for word in sentence.split():
        if word in bad_words:
            #for all words in the bad_words list, check if they occur in the word and if yes, replace them
            sentence = sentence.replace(word, '*' * len(word))
    return sentence

def conspiracy_related(message: str, client, gpt_version) -> bool:
    """
    Function to filter both unrelated messages and messages containing swear words (by calling filter_profanity)
    :param message: the message we want to run the filter on as string
    :param client: the OpenAI client needed to generate the LLM response
    :param gpt_version: The version of ChatGPT we use to generate the response
    :return: the completely filtered message (i.e. completely filtering unrelated messages and masking swear words using filter_profanity
    """
    topic_related = ""
    #as long as ChatGPT did not come to a clear result (i.e. yes or no), ask it again
    counter = 0
    while not topic_related.lower().startswith("yes") and (not topic_related.lower().startswith("no")) and counter < 5:
        #ChatGPT is used to evaluate whether or not the message is related to the topic
        topic_related = client.chat.completions.create(model=gpt_version, messages=[{"role": "user", "content": message + PROFANITY_AI_PROMPT}]).choices[0].message.content
        counter += 1
    #we don't want ChatGPT to generate to many answers to decrease runtime. If it's unsure, we assume the message is topic related.
    if counter == 5:
        topic_related = "yes"
    #if related to the topic, the message can be outputted but first needs to be checked on swear words
    if topic_related.lower().startswith("yes"):
        return True
    else:
        #if unrelated, just return an empty string (i.e. delete the message)
        return False


