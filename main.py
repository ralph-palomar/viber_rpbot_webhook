from flask import Flask, request, jsonify
from waitress import serve
from paste.translogger import TransLogger
from logging.handlers import RotatingFileHandler
import logging
import os
import json
import uuid

api = Flask(__name__)

# SETUP REQUEST PATH
request_uri = '/api/v1/viber-webhook-rpbot/events'

# SETUP LOGGERS
logger = logging.getLogger('waitress')
handler = RotatingFileHandler(filename=__name__+'.log', mode='a', maxBytes=20 * 1024 * 1024, backupCount=5)
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
        logger.info("REQUEST PAYLOAD>>>\n"+json.dumps(payload, indent=3))

        # APPLICATION LOGIC HERE #
        # DEFAULT RESPONSE #
        send_text_message(payload.sender.id, 'Hi, how may I help you?')

        # ---------------------- #

        return create_response({
            "status": "success"
        }), 200
    except Exception as e:
        logger.exception(e)


# HELPER FUNCTIONS
def send_text_message(receiver_id, text_message):
    send_text_request = {
        "receiver": receiver_id,
        "type": "text",
        "sender": {
            "name": "rpbot"
        },
        "text": text_message,
        "tracking_data": uuid.uuid4()
    }

