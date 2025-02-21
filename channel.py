## channel.py - a simple message channel

import json
import os
from dateutil import parser
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from openai import OpenAI
from project_three.profanity import conspiracy_related, filter_profanity

load_dotenv("project_three/secrets.env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gpt_version = "gpt-4o-mini"


# Class-based application configuration
# here messages are not stored like in channels in a database but in a json file
class ConfigClass(object):
    """
     Flask application configuration
    """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'


# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'http://vm146.rz.uni-osnabrueck.de/u012/project_three/hub.wsgi'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = os.environ.get('channel_key')
CHANNEL_NAME = "AluTalk"
CHANNEL_ENDPOINT = "http://vm146.rz.uni-osnabrueck.de/u012/project_three/channel.wsgi"  # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'


@app.cli.command('register')
def register_command() -> None:
    """
    This function sends a POST request to the server and handles possibly occurring errors  
    """
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
                                 "name": CHANNEL_NAME,
                                 "endpoint": CHANNEL_ENDPOINT,
                                 "authkey": CHANNEL_AUTHKEY,
                                 "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                             }))

    # check if an error occurs and return the respective message in case it does
    if response.status_code != 200:
        print("Error creating channel: " + str(response.status_code))
        print(response.text)
        return


def check_authorization(request) -> bool:
    """
    Requests should be authorized in order to be further processed. This function checks authorization and returns True or False. It is to be called on any request.
    :param request: The server request we want to check on authorization
    :return: True or False depending on whether the request is authorized or not
    """
    global CHANNEL_AUTHKEY
    # check if authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True


@app.route('/health', methods=['GET'])
def health_check():
    """
    If the request is not authorized, this function returns an error. Else it converts the channel to a .json file and returns it.
    :return: the channel as a .json object
    """
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name': CHANNEL_NAME}), 200


# GET: Return list of messages
@app.route('/', methods=['GET'])  # list of messages
def home_page():
    """
    Function to set up the homepage and display the welcome message.
    :return: error message or all messages as json objects
    """
    # first check whether the request has a valid header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    # messages that are to old should not be displayed anymore
    delete_messages()
    # get all remaining messages
    messages = read_messages()
    # insert the welcome message at the beginning such that it's the first to be displayed
    messages.insert(0, {'content': "Welcome. This channel was made to discuss your theories about the world "
                                   "(which others might call conspiracy theories). You can start chatting. Please only post "
                                   "conspiracy theory related content and do not use swear words, else your message won't be posted"
                                   "at all or censored. If you want help by our Chatbot, start your message with '/assistant'.",
                        'sender': "Server",
                        'timestamp': str(datetime.now()),
                        })
    # return all messages as json objects
    return jsonify(messages)


# POST: Send a message
@app.route('/', methods=['POST'])  # stores new message
def send_message():
    """
    This function is being called when a user wants to post a message.
    :return: the status of the message (i.e. possible errors or OK, 200)
    """
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    # check if the message has all required attributes, if one is missing return an error
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400
    message['timestamp'] = parse_timestamp(message['timestamp'])
    if not message['timestamp']:
        return "Invalid timestamp", 400
    if not 'extra' in message:
        extra = None
    else:
        extra = message['extra']
    # get all old messages
    messages = read_messages()
    # check if the user wants to interact with the LLM assistant
    if message['content'].lower().startswith("/assistant"):
        messages.append({'content': message['content'],
                         'sender': message['sender'],
                         'timestamp': message['timestamp'],
                         'extra': extra,
                         })
        # generate an AI answer based on the content of the message and append it to the to-be-displayed messages
        messages.append(ai_answer(message['content']))
    else:
        # if the user does not want to interact with the assistant, their message is checked by the filter
        if conspiracy_related(message['content'], client, gpt_version):
            message['content'] = filter_profanity(message['content'])
        else:
            message['content'] = f"The user {message['sender']} tried to send a message which is unrelated to conspiracy theories."
            message['sender'] = "Assistant"
        messages.append({'content': message['content'],
                         'sender': message['sender'],
                         'timestamp': message['timestamp'],
                         'extra': extra,
                         })

    save_messages(messages)
    return "OK", 200


def parse_timestamp(timestamp_str:str):
    try:
        # Replace 'Z' with '+00:00' to make it ISO 8601 compliant
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"

        # Parse timestamp
        dt = parser.isoparse(timestamp_str)

        # Convert to ISO 8601 with 'Z' to ensure JSON compatibility
        print(dt.isoformat().replace("+00:00", "Z"))
        return dt.isoformat().replace("+00:00", "Z")

    except Exception:
        return None  # Return None if parsing fails

def read_messages():
    """
    This function loads all the messages we have saved from previous interactions.
    :return: these loaded messages
    """
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages


def save_messages(messages) -> None:
    """
    The opposite of read_messages -> Function that gets messages as input and saves them in json format.
    :param messages: the messges we want to save as json
    """
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)


def delete_messages() -> None:
    """
    Function that deletes all messages older than 25h.
    """
    messages = read_messages()
    current_time = datetime.now()  # get current time
    threshold = timedelta(hours=25)

    # Filter messages
    filtered_messages = [
        message for message in messages
        if datetime.fromisoformat(message["timestamp"].rstrip('Z')) >= current_time - threshold
    ]
    # save only the messages that are not deleted by the filter
    save_messages(filtered_messages)


def ai_answer(message):
    """
    This function is called if the user asks for help by the AI (using the keyword /assistant).
    :param message: the user message where they ask for assistance.
    :return: the answer generated by ChatGPT
    """
    content = client.chat.completions.create(model=gpt_version, messages=[{"role": "user", "content": message + "Please"
                                                                                                                " answer as if you were whole-heartedly believing into all conspiracy theories that have ever been invented. E.g. you"
                                                                                                                " should be 100% certain that the earth is flat and insult any person claiming something else. Keep your answer short and it should not sound to intelligent."}])

    print(content)
    return {'content': content.choices[0].message.content,
            'sender': "Assistant",
            'timestamp': str(datetime.now()),
            'extra': "",
            }


import traceback


@app.errorhandler(500)
def internal_error(exception):
    return "<pre>" + traceback.format_exc() + "</pre>"


# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == '__main__':
    app.run(port=5001, debug=True)
