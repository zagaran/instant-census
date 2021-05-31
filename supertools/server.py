from database.backbone.servers import Server
from utils.server import all_servers, disk_test, my_ip_address, gethostname,\
    get_server_status
from utils.email_utils import send_eng_html, send_eng_email
from utils.time import now
from jinja2 import Environment, PackageLoader

#OTHER_SERVERS_TO_CHECK = ["s3lab.instantcensus.com"]
OTHER_SERVERS_TO_CHECK = []

def server_statuses():
    servers = all_servers() + OTHER_SERVERS_TO_CHECK
    statuses = dict((server, {'status': None, 'mongo': None}) for server in servers)
    for server in servers:
        statuses[server]['name'] = Server.get_name(server)
        status, mongo = get_server_status(server)
        statuses[server]['status'] = status
        statuses[server]['mongo'] = mongo
    return statuses


def email_server_summary():
    statuses = server_statuses()
    template = email_template('emails/server_status.html')
    html = template.render(data=statuses, time=now().strftime('%Y-%m-%d %H:%M'))
    for _server, status in statuses.iteritems():
        if status['status'] not in range(200, 300) or not status['mongo']:
            subject = 'THE SYSTEM...IS DOWN! THE SYSTEM...IS DOWN!'
            send_eng_html(subject, html)
            return

def email_template(template_path):
    env = Environment(loader=PackageLoader('app', 'frontend/templates'))
    template = env.get_template(template_path)
    return template

#TODO: we should probably make this do a conditional Sentry alert instead of always email.
def email_disk_alerts():
    if not disk_test():
        send_eng_email("SERVER LOW ON DISK SPACE!",
                       str(my_ip_address()) + "\n" + str(gethostname()))
