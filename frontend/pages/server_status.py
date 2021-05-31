from utils.database import mongo_ping
from utils.time import now
from flask import Blueprint, request, render_template
from socket import gethostname

server_status = Blueprint('server_status', __name__)

@server_status.route('/ping', methods=["POST"])
def status_ping():
    if mongo_ping():
        return 'pong'
    else:
        return 'mongo check failed'

@server_status.route('/server_status/status', methods=["POST"])
def dashboard_status():
    data = request.json
    return server_summary(data)

def server_summary(data):
    return render_template('emails/server_status.html',
                           data=data, time=now().strftime('%Y-%m-%d %H:%M'))

@server_status.route('/hostname', methods=["POST"])
def hostname():
    return str(gethostname())
