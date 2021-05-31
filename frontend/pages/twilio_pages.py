from backend.incoming.entry_points import on_receive
from database.backbone.servers import Server
from database.tracking.messages import DroppedMessage, ControlMessage, Message, RawMessage
from flask import Blueprint, request, abort, Response
from time import sleep
from utils.email_utils import send_eng_email
from utils.logging import log_error, log_warning
from utils.server import ip_of_phonenum
from utils.time import now
from utils.twilio_utils import serve_twilio_response

twilio_pages = Blueprint('twilio_pages', __name__)

TWILIO_BAD_DELIVERY_STATUSES = ["undelivered", "failed"]

@twilio_pages.route('/sms_in', methods=['GET', 'POST'])
def receive_sms():
    try:
        receive_time = now()
        from_number = request.values.get("From")
        ic_number = request.values.get("To")
        #date_sent = request.values.get("DateSent")
        twilio_message_sid = request.values.get("MessageSid")
        message_body = request.values.get("Body", "")
        RawMessage.store(from_number, message_body, ic_number, receive_time, twilio_message_sid)
        on_receive(ic_number, from_number, message_body, receive_time, twilio_message_sid=twilio_message_sid)
        return serve_twilio_response()
    except Exception as e:
        log_error(e, "Error in receive_sms")
        # abort(503)
        xml = '<?xml version="1.0" encoding="UTF-8" ?><Response></Response>'
        return Response(xml, status=400, mimetype="text/xml")


@twilio_pages.route('/twilio/alert', methods=["GET", "POST"])
def twilio_alert():
    receive_time = now()
    from_number = request.values.get('From')
    ic_number = request.values.get('To')
    #date_sent = request.values.get('DateSent')
    twilio_message_sid = request.values.get("MessageSid")
    message_body = request.values.get('Body')
    message = str(DroppedMessage.store(from_number, message_body, ic_number, receive_time, twilio_message_sid))
    try:
        ip_addr = ip_of_phonenum(ic_number)
        message += "\n\nServer IP Address: " + str(ip_addr)
        message += "\nServer Name: " + Server.get_name(ip_addr)
    except Exception as e:
        log_error(e)
    send_eng_email("DROPPED TEXT ALERT", message)
    return serve_twilio_response()


@twilio_pages.route('/reject_call', methods=['GET', 'POST'])
def reject_calls():
    return serve_twilio_response(reject=True)


@twilio_pages.route("/twilio/callback", methods=["POST"])
def twilio_callback():
    # TODO: Graceful handling of twilio callbacks that won't overload workers
    message_sid = request.values.get("MessageSid")
    message_status = request.values.get("MessageStatus")
    error_code = request.values.get("ErrorCode")
    current_time = now()
    # if bad delivery status, notify engineering
    # TODO: handling non-sent messages
    if error_code in TWILIO_BAD_DELIVERY_STATUSES:
        send_eng_email("Error: Twilio message failed to send",
            "Message SID: %s\nMessage Status: %s\nError Code: %s" % (message_sid, message_status, error_code))
    # get message
    message = retrieve_message_by_twilio_sid(message_sid)
    # update message
    try:
        message.update({
            "twilio_error_code": error_code,
            "twilio_message_status": message_status,
            "twilio_update_time": current_time,
        })
    except Exception as e:
        log_error(e, "No message found for twilio callback with sid '%s' and status '%s'." % (message_sid, message_status))
    return serve_twilio_response()


# recursive function that sleeps if message doesn't exist in database yet and twilio callback happened already
def retrieve_message_by_twilio_sid(message_sid, retries=5):
    if retries != 0:
        # get message
        message = Message(twilio_message_sid=message_sid)
        if not message:
            message = ControlMessage(twilio_message_sid=message_sid)
        if not message:
            sleep(2)
            return retrieve_message_by_twilio_sid(message_sid, retries-1)
        return message
    else:
        log_warning("Unable to fetch twilio message by twilio_sid.")
        return None