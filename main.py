from flask import Flask, request, jsonify
from waitress import serve
from paste.translogger import TransLogger
from logging.handlers import RotatingFileHandler
import logging
import os
import json

api = Flask(__name__)

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


@api.route('/api/v1/viber-webhook-rpbot/events', methods=['OPTIONS'])
def preflight():
    return create_response({}), 200


def create_response(response_payload):
    try:
        response = jsonify(response_payload)
        response.headers['Access-Control-Allow-Origin'] = os.environ['ALLOWED_ORIGIN']
        response.headers['Access-Control-Allow-Headers'] = 'X-Viber-Auth-Token, Authorization, JWT, Overwrite, Destination, Content-Type, Depth, User-Agent, Translate, Range, Content-Range, Timeout, X-File-Size, X-Requested-With, If-Modified-Since, X-File-Name, Cache-Control, Location, Lock-Token, If'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS, POST, PUT, DELETE'
        response.headers['Access-Control-Max-Age'] = 3600
        return response
    except Exception as e:
        logger.exception(e)


@api.route('/api/v1/viber-webhook-rpbot/events', methods=['POST'])
def process_event():
    try:
        payload = request.json
        logger.info(json.dumps(payload, indent=3))
        return create_response({}), 200
    except Exception as e:
        logger.exception(e)
