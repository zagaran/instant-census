from database.analytics.system_load import CronTimes
from utils.time import now

def safe_to_deploy():
    """ Checks if the hourly job is currently running """
    try:
        last_hourly = CronTimes(page_size=1, ascending=False)[0]["start_time"]
    except IndexError:
        return False
    last_hourly = last_hourly.replace(minute=0, second=0, microsecond=0)
    return last_hourly == now().replace(minute=0, second=0, microsecond=0)
