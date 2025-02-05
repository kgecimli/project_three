## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
from datetime import datetime, timedelta
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv("secrets.env")

client = OpenAI(api_key=os.getenv("openai_api_key"))
gpt_version = os.getenv("GPT_VERSION")

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

HUB_URL = 'http://localhost:5555' #need to know where the hub is
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "The One and Only Channel"
CHANNEL_ENDPOINT = "http://localhost:5001" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

#now we have a command in flask app store
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
    messages.insert(0,{'content': "Welcome. You can start chatting. If you want help by"
                                  "our Chatbot, start your message with '/assistant'",
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
    messages.append({'content': message['content'],
                     'sender': message['sender'],
                     'timestamp': message['timestamp'],
                     'extra': extra,
                     })
    if message['content'].lowercase().startswith("/assistant)"):
            messages.append(ai_answer(message['content']))
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
        if datetime.fromisoformat(message["timestamp"]) >= current_time - threshold
    ]
    save_messages(filtered_messages)

def ai_answer(message):
    content = client.chat.completions.create(model=gpt_version, messages=message)
    return {'content': content.choices[0].message.content,
                     'sender': "Assistant",
                     'timestamp': datetime.now(),
                     'extra': "",
                     }

# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == '__main__':
    app.run(port=5001, debug=True)
