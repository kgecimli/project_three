## channel.py - a simple message channel

from flask import Flask, request, render_template, jsonify
from datetime import datetime, timedelta
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import os
import re

from project_three.profanity import filter_complete

load_dotenv("project_three/secrets.env")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
gpt_version = "gpt-4o-mini"

# Class-based application configuration
#here messages are not stores like in channels in a database but in a json file
class ConfigClass(object):
    """ Flask application config """

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
CHANNEL_ENDPOINT = "http://vm146.rz.uni-osnabrueck.de/u012/project_three/channel.wsgi" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
                                "name": CHANNEL_NAME,
                                "endpoint": CHANNEL_ENDPOINT,
                                "authkey": CHANNEL_AUTHKEY,
                                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                             }))

    if response.status_code != 200:
        print("Error creating channel: "+str(response.status_code))
        print(response.text)
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

# GET: Return list of messages
@app.route('/', methods=['GET']) #list of messages
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    delete_messages()
    messages = read_messages()
    messages.insert(0,{'content': "Welcome. This channel was made to discuss your theories about the world "
                                  "(which others might call conspiracy theories). You can start chatting. Please only post "
                                  "conspiracy theory related content and do not use swear words, else your message won't be posted"
                                  "at all or censored. If you want help by our Chatbot, start your message with '/assistant'.",
                     'sender': "Server",
                     'timestamp': str(datetime.now()),
                     })
    return jsonify(messages)


# POST: Send a message
@app.route('/', methods=['POST']) #stores new message
def send_message():
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400

    if not 'extra' in message:
        extra = None
    else:
        extra = message['extra']
    # add message to messages
    messages = read_messages()
    if message['content'].lower().startswith("/assistant"):
        messages.append({'content': message['content'],
                         'sender': message['sender'],
                         'timestamp': message['timestamp'],
                         'extra': extra,
                         })
        messages.append(ai_answer(message['content']))
    else:
        message['content'] = filter_complete(message['content'], client, gpt_version)
        messages.append({'content': message['content'],
                     'sender': message['sender'],
                     'timestamp': message['timestamp'],
                     'extra': extra,
                     })

    save_messages(messages)
    return "OK", 200

def read_messages():
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

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)

def delete_messages():
    messages = read_messages()
    current_time = datetime.now()  # Get current time in UTC
    threshold = timedelta(hours=25)

    # Filter messages
    filtered_messages = [
        message for message in messages
        if datetime.fromisoformat(message["timestamp"].rstrip('Z')) >= current_time - threshold
    ]
    save_messages(filtered_messages)

def ai_answer(message):
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
   return "<pre>"+traceback.format_exc()+"</pre>"
# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == '__main__':
    app.run(port=5001, debug=True)
