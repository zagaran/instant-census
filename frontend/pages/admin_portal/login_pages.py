from datetime import timedelta
from constants.database import INTERNAL_SUPER_ADMIN_EMAIL
import urllib
import hmac

from flask import Blueprint, request, redirect, flash, json, abort

from backend.admin_portal.login_pages_helpers import check_token
from database.tracking.admins import Admin
from frontend import templating, auth
from conf.secure import APP_SECRET_KEY
from conf.settings import DISABLE_PASSWORD_RESET
from utils.email_utils import send_html
from utils.logging import log_error, log_warning
from utils.time import now


login_pages = Blueprint('login', __name__)


@login_pages.route("/login", methods=["GET", "POST"])
@templating.template("admin_portal/login_page.html")
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email:
            flash("Please enter an email address.", "error")
            return {
                "email": email,
                "DISABLE_PASSWORD_RESET": DISABLE_PASSWORD_RESET
            }
        if not password:
            flash("Please enter a password.", "error")
            return {
                "email": email,
                "DISABLE_PASSWORD_RESET": DISABLE_PASSWORD_RESET
            }
        # TODO: this is gonna break - change to admin
        admin = Admin.get_admin(email.lower(), password)
        if admin:
            auth.set_loggedin_admin(admin)
            admin.update({"last_login_time": now()})
            if admin["email"] == INTERNAL_SUPER_ADMIN_EMAIL:
                admin.update({"hashed_password": None})
            return redirect("/cohorts")
        flash("Email or password is incorrect.", "error")
        return {
            "email": email,
            "DISABLE_PASSWORD_RESET": DISABLE_PASSWORD_RESET
        }
    return {"DISABLE_PASSWORD_RESET": DISABLE_PASSWORD_RESET}


@login_pages.route("/logout", methods=["GET", "POST"])
def logout():
    auth.del_loggedin_admin()
    return redirect("/")


@login_pages.route("/reset_password", methods=["GET", "POST"])
@templating.template("admin_portal/reset_password.html")
def reset_password():
    if DISABLE_PASSWORD_RESET:
        abort(403)
    if request.method == "GET":
        return {}
    else:
        email = request.form.get("email").lower().strip()
        if not email or email == "None":
            flash("Please enter an email address.", "error")
            return {
                "email": email
            }
        admin = Admin(email=email)
        if not admin:
            log_warning("No admin matching email '%s'; password reset request failed." % email)
        else:
            current_time = now().replace(microsecond=0)
            last_reset = admin["last_reset_password_request_time"]
            # Throttle password reset requests. (to e.g. prevent spamming, make attacks slower)
            if last_reset and (current_time - last_reset) < timedelta(minutes=10):
                flash(("Only one password reset request allowed every 10 minutes. Please " +
                       "try again in a few minutes."), "error")
                return {
                    "email": email
                }
            try:
                # Payload elements are used to create the token hash. If any of the elements changes by the time
                # token is used to reset a password, token becomes invalid. For example, if they manage to login
                # again, they make another request, they change their password, etc since requesting a password reset,
                # the token becomes invalid.
                payload = {
                    "email": email,
                    "hashed_password": admin["hashed_password"],
                    "last_login_time": admin["last_login_time"],
                    "last_reset_password_request_time": str(current_time)
                }
                # The security of all this depends on APP_SECRET_KEY being secret and strong
                token = hmac.new(APP_SECRET_KEY, json.dumps(payload)).hexdigest()
                # password rest URL being generated
                url = "new_password?%s" % urllib.urlencode({"token": token})
                # admin updated
                admin["last_reset_password_request_time"] = current_time
                admin["last_reset_password_token"] = token
                admin.save()
                # TODO: make branded email and move to different file
                # request.url_root will return 'https://subdomain.instantcensus.com'
                send_html(
                    email,
                    "Instant Census: password reset request",
                    ("Hello!<br /><br />You recently requested to reset your Instant Census password. " +
                     "To reset your password, please click the link below:<br /><br />" +
                     "<a href='%s%s' target='_blank'>Reset my password</a><br /><br />" +
                     "If you did not request a password reset, please let us know at " +
                     "<a href='mailto:support@instantcensus.com'>support@instantcensus.com</a>.") % \
                    (request.url_root, url)
                )
            except Exception as e:
                log_error(e, message="Error generating password reset token for email %s" % email, time=True)
                flash("An error occurred while resetting your password.", "error")
                return {
                    "email": email
                }
        # even if email isn't in the database, display this message to reveal little information
        flash("A password recovery email has been sent to %s if it is valid." % email, "success")
        return {
            "email": email
        }


@login_pages.route("/new_password", methods=["GET", "POST"])
@templating.template("admin_portal/new_password.html")
def new_password():
    if DISABLE_PASSWORD_RESET:
        abort(403)
    # if admin click on url to reset password
    if request.method == "GET":
        token = request.args.get("token")
        # if successful token authentication, let admin change password
        if check_token(token):
            return {
                "authenticated": True,
                "token": token
            }
        # token not authenticated
        else:
            return {
                "authenticated": False
            }
    else:
        token = request.form.get("token")
        password = request.form.get("password")
        confirm_password = request.form.get("password_confirm")
        # check passwords and confirm they match
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return {
                "authenticated": True,
                "token": token
            }
        # if successful token authentication, reset password
        if check_token(token):
            admin = Admin(last_reset_password_token=str(token))
            admin.set_password(password)
            flash("New password successfully set!", "success")
            return redirect("/login")
        # token not authenticated
        else:
            return {
                "authenticated": False
            }
