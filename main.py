from flask import Flask, request, jsonify
from waitress import serve
from paste.translogger import TransLogger
from logging.handlers import RotatingFileHandler
from pymemcache.client import base
import logging
import os
import json
import uuid
import requests
import qrcode
import qrcode.image

api = Flask(__name__)

# SETUP CACHE CLIENT
cache = base.Client(('localhost', 11211))

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

# GLOBAL VARIABLES
default_keyboard_options = [
    {
        "ActionType": "reply",
        "ActionBody": "covid_contact_tracing",
        "Text": "Submit COVID Contact Tracing Info",
        "TextSize": "regular"
    },
    {
        "ActionType": "reply",
        "ActionBody": "qr_code_covid",
        "Text": "Generate QR Code for COVID Contact Tracing",
        "TextSize": "regular"
    }
]


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
        log_payload("ORIGINATED FROM VIBER", payload)

        # APPLICATION LOGIC HERE #
        event = payload.get('event', None)
        sender = payload.get('sender', None)
        message = payload.get('message', None)

        if event is not None and sender is not None and sender.get('id', None) is not None and message is not None:
            sender_id = sender.get('id')
            tracking_data = message.get('tracking_data', None)

            if tracking_data is None and event == "message" and message is not None and any([option['ActionBody'] != message['text'] for option in default_keyboard_options]):
                tracking_id = send_default_response(sender_id, tracking_id=None)
                cache.set(key=tracking_id, value={}, expire=300)

            else:
                cached_tracking_data = cache.get(tracking_data, None)
                tracking_data_dict = json.loads(cached_tracking_data) if cached_tracking_data is not None else {}
                operation = tracking_data_dict.get('op', None)

                if cached_tracking_data is None and operation is None:
                    if message['text'] == "covid_contact_tracing":
                        send_plain_text_message(sender_id, "Submit COVID Contact Tracing Info", tracking_data)
                    elif message['text'] == "qr_code_covid":
                        tracking_id = send_plain_text_message(sender_id, "Started COVID QR Code Generator", tracking_data)
                        new_cached_tracking_data = {
                            "id": tracking_id,
                            "op": "qr_code_covid",
                            "stage": "first_name"
                        }
                        cache.set(key=tracking_id, value=json.dumps(new_cached_tracking_data), expire=300)
                        send_plain_text_message(sender_id, "Enter your FIRST NAME", tracking_id)
                    else:
                        send_default_response(sender_id, tracking_id=None)
                else:
                    stage = tracking_data_dict['stage']
                    tracking_id = tracking_data_dict['id']
                    if stage == "first_name":
                        tracking_data_dict['firstName'] = message['text']
                        tracking_data_dict['stage'] = "last_name"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Enter your LAST NAME", tracking_id)
                    elif stage == "last_name":
                        tracking_data_dict['lastName'] = message['text']
                        tracking_data_dict['stage'] = "middle_name"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Enter your MIDDLE NAME", tracking_id)
                    elif stage == "middle_name":
                        tracking_data_dict['middleName'] = message['text']
                        tracking_data_dict['stage'] = "unit_house_building"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Enter your UNIT NO./HOUSE NO./BUILDING", tracking_id)
                    elif stage == "unit_house_building":
                        tracking_data_dict['unitHouseBldg'] = message['text']
                        tracking_data_dict['stage'] = "street_address"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Enter your STREET ADDRESS", tracking_id)
                    elif stage == "street_address":
                        tracking_data_dict['streetAddress'] = message['text']
                        tracking_data_dict['stage'] = "city"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Enter your CITY", tracking_id)
                    elif stage == "city":
                        tracking_data_dict['city'] = message['text']
                        tracking_data_dict['stage'] = "zip_code"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Enter your ZIP CODE", tracking_id)
                    elif stage == "zip_code":
                        tracking_data_dict['zipCode'] = message['text']
                        tracking_data_dict['stage'] = "done"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Enter your CONTACT NUMBER", tracking_id)
                    else:
                        tracking_data_dict['contactNumber'] = message['text']
                        tracking_data_dict['stage'] = "done"
                        cache.set(key=tracking_id, value=json.dumps(tracking_data_dict), expire=300)
                        send_plain_text_message(sender_id, "Thank you! Generating QR Code!", tracking_id)
                        log_payload("QR CODE DATA", tracking_data_dict)
                        qr_data = json.dumps(tracking_data_dict)
                        qrcode_f = open(f'/home/ralphp/scripts/qrcodes/{tracking_id}.png', 'w')
                        qrcode_f.write(qrcode.make(qr_data))
                        qrcode_f.close()

        return create_response({
            "status": "success"
        }), 200

    except Exception as e:
        logger.exception(e)


# HELPER FUNCTIONS
def send_default_response(receiver_id, tracking_id):
    tracking_data = uuid.uuid4().hex if tracking_id is None else tracking_id
    send_text_message({
        "receiver": receiver_id,
        "min_api_version": 1,
        "type": "text",
        "text": f'Hey beautiful human, how may I help you?',
        "tracking_data": tracking_data,
        "keyboard": {
            "Type": "keyboard",
            "DefaultHeight": True,
            "Buttons": default_keyboard_options
        }
    })
    return tracking_data


def send_plain_text_message(receiver_id, text_message, tracking_id):
    tracking_data = uuid.uuid4().hex if tracking_id is None else tracking_id
    send_text_message({
        "receiver": receiver_id,
        "min_api_version": 1,
        "type": "text",
        "text": text_message,
        "tracking_data": tracking_data,
    })
    return tracking_data


def send_text_message(send_text_request):
    log_payload("SEND TEXT MESSAGE", send_text_request)
    requests.post('https://chatapi.viber.com/pa/send_message', json=send_text_request, headers=viber_request_headers)


def get_user_details(user_id):
    get_user_details_request = {
        "id": user_id
    }
    get_user_details_response = requests.post('https://chatapi.viber.com/pa/get_user_details', json=get_user_details_request, headers=viber_request_headers)
    get_user_details_json_response = get_user_details_response.json()
    log_payload("GET USER DETAILS", get_user_details_json_response)
    return get_user_details_json_response


def get_account_info():
    get_account_info_response = requests.post('https://chatapi.viber.com/pa/get_account_info', json={}, headers=viber_request_headers)
    get_account_info_json_response = get_account_info_response.json()
    log_payload("GET ACCOUNT INFO", get_account_info_json_response)
    return get_account_info_json_response


def log_payload(payload_id, payload):
    logger.info(f'{payload_id}>>>\n{json.dumps(payload, indent=3)}')
