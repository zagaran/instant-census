from database.tracking.users import Status
from utils.actions import Action


@Action('unused.set_status')
def set_status(user, status):
    get_status = Status.__dict__.get(status)
    if get_status is None: return False
    user.set_status(status)
    return True
