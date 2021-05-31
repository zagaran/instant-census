from database.tracking.users import User
from backend.outgoing.dispatcher import send_welcome
from constants.users import Status
from flask import Blueprint, request

custom = Blueprint('custom', __name__)

@custom.route('/activate', methods=["GET", "POST"])
def activate():
    _id = request.args["id"]
    user = User(_id)
    if user:
        if user["status"] == Status.pending:
            user.set_status(Status.active)
            send_welcome(user)
            return "User activated"
        return "User already active"
    return "Invalid user"
