from flask import Flask, request, jsonify
from waitress import serve
from paste.translogger import TransLogger
from logging.handlers import RotatingFileHandler
import logging
import os
import json
import uuid
import requests

api = Flask(__name__)

# SETUP REQUEST PATH
request_uri = '/api/v1/viber-webhook-rpbot/events'

# SETUP VIBER REQUEST TOKEN
viber_request_token = os.environ['VIBER_REQUEST_TOKEN']
viber_request_headers = {
    "Content-Type": "application/json",
    "X-Viber-Auth-Token": viber_request_token
}

# SETUP LOGGERS
logger = logging.getLogger('waitress')
handler = RotatingFileHandler(filename=f'{__name__}.log', mode='a', maxBytes=20 * 1024 * 1024, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(funcName)s (%(lineno)d) %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# SETUP MAIN ENTRY
if __name__ == '__main__':
    try:
        serve(TransLogger(api, logger=logger), host='0.0.0.0', port=5000, threads=16)
    except Exception as ex:
        logger.exception(ex)


@api.route(request_uri, methods=['OPTIONS'])
def pre_flight():
    return create_response({}), 200


def create_response(response_payload):
    try:
        response = jsonify(response_payload)
        response.headers['Access-Control-Allow-Origin'] = os.environ['ALLOWED_ORIGIN']
        response.headers['Access-Control-Allow-Headers'] = 'X-Viber-Auth-Token, Authorization, JWT, Overwrite, Destination, Content-Type, Depth, User-Agent, Translate, Range, Content-Range, Timeout, X-File-Size, X-Requested-With, If-Modified-Since, X-File-Name, Cache-Control, Location, Lock-Token, If'
        response.headers['Access-Control-Allow-Methods'] = 'OPTIONS, GET, POST, PUT, PATCH, DELETE'
        response.headers['Access-Control-Max-Age'] = 3600
        return response
    except Exception as e:
        logger.exception(e)


@api.route(request_uri, methods=['POST'])
def process_event():
    try:
        payload = request.json
        log_request("ORIGINATED FROM VIBER", payload)

        # APPLICATION LOGIC HERE #
        sender = payload.get('sender', None)
        # DEFAULT RESPONSE #
        if sender is not None and sender.get('id', None) is not None:
            send_text_message(sender.get('id'), 'Hi, how may I help you?')

        # ---------------------- #

        return create_response({
            "status": "success"
        }), 200
    except Exception as e:
        logger.exception(e)


# HELPER FUNCTIONS
def send_text_message(receiver_id, text_message, keyboard={}):
    send_text_request = {
        "receiver": receiver_id,
        "min_api_version": 1,
        "type": "text",
        "text": text_message,
        "tracking_data": uuid.uuid4().hex,
        "keyboard": keyboard
    }
    log_request("SEND TEXT MESSAGE REPLY", send_text_request)
    response = requests.post('https://chatapi.viber.com/pa/send_message', json=send_text_request, headers=viber_request_headers)
    log_request("SEND TEXT MESSAGE API RESPONSE", response)


def log_request(request_id, payload):
    logger.info(f'{request_id}>>>\n{json.dumps(payload, indent=3)}')

