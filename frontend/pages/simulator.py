import calendar
from datetime import timedelta
from flask import Blueprint, request, abort, jsonify, session, redirect
from backend.incoming.entry_points import every_hour_core, on_receive
from backend.incoming.new_user import onboard_user
from database.analytics.responses import Responses
from database.tracking.users import User
from database.tracking.schedule_execution import ScheduleExecutions
from frontend import templating, auth
from utils.time import now, set_now
from utils.server import PRODUCTION
from mongolia.constants import ID_KEY

simulator = Blueprint('simulator', __name__)

@simulator.route("/simulator", methods=["GET", "POST"])
@auth.admin
@templating.template('simulator.html')
def day_simulator():
    # TODO: have simulator work in production; this requires not using artifical time
    if PRODUCTION: abort(404)
    user = User.get_test_user()
    
    if "end_sim" in request.form:
        set_now(None)
        for i in user.all_messages():
            i.remove()
        for i in Responses(user_id=user[ID_KEY]):
            i.remove()
        for i in ScheduleExecutions(user_id=user[ID_KEY]):
            i.remove()
        user.update(current_execution=None)
        user.update_schedule_executions(now())
    elif request.method == "POST":
        if "next_day" in request.form:
            set_now(now() + timedelta(days=1))
        elif "next_hour" in request.form:
            set_now(now() + timedelta(hours=1))
        elif "onboard_user" in request.form:
            onboard_user(user, now())
        every_hour_core(user, now())
        return redirect("/simulator")
    
    # Warning: the following is using artificial time; this will log you out
    # if you try to simulate the past
    session["expiry"] = now() + timedelta(days=5)
    
    executions = ScheduleExecutions(user_id=user[ID_KEY])
    for execution in executions:
        del execution["user_id"]
    return {"user": user,
            "calendar": calendar.HTMLCalendar().formatmonth(now().year, now().month),
            "day_of_month": now().day,
            "hour": now().hour,
            "schedule_executions": executions,
    }

@simulator.route("/sendmessage", methods=["POST"])
@auth.admin
def sendmessage():
    if "message" not in request.form: abort(404)
    message = request.form["message"]
    user = User.get_test_user()
    print("received message '%s'" % message)
    set_now(now() + timedelta(minutes=1))
    on_receive(user["ic_number"], user["phonenum"], message, now(), delay=False)
    return jsonify({"success" : True, "error_message": None})
