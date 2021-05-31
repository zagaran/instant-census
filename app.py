import sys
import traceback

import jinja2
from bson import ObjectId
from flask import Flask, render_template, redirect, session, request, flash
from flaskext.markdown import Markdown
from mongolia import ID_KEY
from raven.contrib.flask import Sentry
from raven.exceptions import InvalidDsn

from backend.outgoing.exit_points import over_usage_limit
from conf.secure import APP_SECRET_KEY, SENTRY_DSN, JS_SENTRY_DSN
from conf.settings import (NEEDS_REVIEW_COUNTS, ADMIN_LEVEL_VISIBILITY, DATA_REPORTS_FEATURE,
    SHOW_DELETED_USERS)
from constants.database import EXCLUDE_DELETED_USERS_QUERY
from constants.messages import OVER_USAGE_LIMIT_MESSAGE
from constants.users import AdminTypes
from database.backbone.cohorts import Cohorts
from database.tracking.users import Users
from frontend.auth import is_logged_in, is_admin_type
from frontend.pages import (twilio_pages, server_status, simulator, cron_dispatch,
    demo, api_pages)
from frontend.pages.admin_portal import (survey_builder, cohorts_dashboard,
    user_management, message_sender, login_pages, download_data,
    needs_review, docs, data_reports)
from utils.logging import log_error

### This is the codebase version number
IC_VERSION_NUMBER = "v1.1"
###


def subdomain(directory):
    app = Flask(__name__, static_folder=directory + "/static")
    Markdown(app, extensions=['markdown.extensions.toc'])
    app.secret_key = APP_SECRET_KEY
    loader = [app.jinja_loader, jinja2.FileSystemLoader(directory + "/templates")]
    app.jinja_loader = jinja2.ChoiceLoader(loader)
    return app

app = subdomain("frontend")
app.register_blueprint(twilio_pages.twilio_pages)
app.register_blueprint(simulator.simulator)
app.register_blueprint(cohorts_dashboard.cohorts_dashboard)
app.register_blueprint(login_pages.login_pages)
app.register_blueprint(server_status.server_status)
app.register_blueprint(api_pages.api_pages)
app.register_blueprint(user_management.user_management)
app.register_blueprint(survey_builder.survey_builder)
app.register_blueprint(message_sender.message_sender)
app.register_blueprint(download_data.download_data)
app.register_blueprint(needs_review.needs_review)
app.register_blueprint(cron_dispatch.cron_dispatch)
app.register_blueprint(docs.docs)
app.register_blueprint(data_reports.data_reports)
app.register_blueprint(demo.demo)


# Max upload size of 15 MB
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024


# Insert the sentry error reporting system if it exists
try:
    sentry = Sentry(app, dsn=SENTRY_DSN)
except InvalidDsn:
    print "\nThe sentry DSN provided, '%s', is not valid. Running without sentry.\n"\
          "(Stick http[s]:// at the beginning of your dsn if you are getting a warnings.warn message.)" % SENTRY_DSN
    JS_SENTRY_DSN = None

@app.route('/')
def main_home_page():
    if is_logged_in():
        return redirect("/cohorts")
    return redirect("/login")

@app.route('/broken')
def broken_page():
    [][0]
    return {}

@app.context_processor
def inject_unhandled_users_count():
    # hacky fix for when user is not logged in, do not inject unhandled users count
    if not NEEDS_REVIEW_COUNTS or not session or "admin_id" not in session:
        return {"unhandled_user_count": ""}
    users_filter_kwargs = {
        "needs_review": True
    }
    # do not count if deleted and option isn't set
    if not SHOW_DELETED_USERS:
        users_filter_kwargs["status"] = EXCLUDE_DELETED_USERS_QUERY
    users = Users(**users_filter_kwargs)
    # if admin-level visibility is enabled, only show users attached to the admin
    if ADMIN_LEVEL_VISIBILITY and not is_admin_type([AdminTypes.super]):
        cohorts = [c[ID_KEY] for c in Cohorts.retrieve_by_admin(ObjectId(session["admin_id"]))]
        users = [user for user in users if user["cohort_id"] in cohorts]
    unhandled_user_count = len(users)
    if unhandled_user_count == 0:
        unhandled_user_count = ""
    return {"unhandled_user_count": unhandled_user_count}

@app.context_processor
def app_level_features():
    return {"DATA_REPORTS_FEATURE": DATA_REPORTS_FEATURE,
            "JS_SENTRY_DSN": JS_SENTRY_DSN}

@app.context_processor
def monthly_usage_limit_warning():
    if over_usage_limit():
        flash(OVER_USAGE_LIMIT_MESSAGE, "warning")
    return {}

############################################
########### EXCEPTION HANDLERS #############
############################################

# @app.errorhandler(APIException)
# def handle_exception(error):
#     response = jsonify(error.to_dict())
#     response.status_code = error.status_code
#     return response

#NOTE: ajax 'post' in functions.js depends on this being commented out
#@app.errorhandler(400)
#def e400(e):
#    return render_template("400.html"), 400

@app.errorhandler(404)
def e404(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def e500_text(e):
    try:
        log_error(e, "request.url is: %s" % request.url)
        if is_logged_in([AdminTypes.super]):
            stacktrace = traceback.format_exc()
            return str(stacktrace.replace("\n", "<br/>"))
    except Exception as e:
        log_error(e)
    return render_template("500.html"), 500


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'prod':
        app.run(host='0.0.0.0', port=80)
    else:
        app.run(debug=True)
