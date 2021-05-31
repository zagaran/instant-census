from bson import ObjectId
from flask import Blueprint, request, session, flash, redirect
from pytz import all_timezones

from constants.database import ANSWER_VALUE_DISPLAY
from database.tracking.admins import Admin
from frontend import templating, auth
from utils.time import now

docs = Blueprint("docs", __name__)


@docs.route("/docs")
@auth.admin
@templating.template('admin_portal/docs.html')
def render_docs():
    return {
        "page": "docs",
        "ANSWER_VALUE_DISPLAY": ANSWER_VALUE_DISPLAY,
        "TIMEZONE_LIST": all_timezones
    }


@docs.route("/tos", methods=["GET", "POST"])
@templating.template('admin_portal/tos.html')
def render_terms():
    if request.method == "POST":
        tos_checkbox = request.form.get("tos_checkbox")
        if tos_checkbox == "on":
            admin = Admin(ObjectId(session["admin_id"]))
            admin.update({"signed_tos_timestamp": now()})
            session["tos"] = True
            flash("Welcome to Instant Census!", "success")
            return redirect("/cohorts")
        else:
            flash("You must click the checkbox to agree before continuing.", "error")
            return {}
    else:
        return {}

