TEST_USER_PHONENUM = "+18888888888"
ADMIN_USER_PHONENUM = "+10000000000"

STATUSES = [
    "active",
    "deleted",
    "disabled",
    "inactive",
    "invalid",
    "paused",
    "pending",
    "waitlist",
    "completed"
]


class Status(object):
    active = "active"       # enabled
    deleted = "deleted"     # deleted by admin
    disabled = "disabled"   # disabled from texting STOP
    inactive = "inactive"   # disabled due to not texting us for too long
    invalid = "invalid"     # requires a valid access code to become active
    paused = "paused"       # temporarily suspended by admin
    pending = "pending"     # waiting for /activate or them to text START
    waitlist = "waitlist"   # waiting for room in the cohort
    completed = "completed" # finished with survey(s)

class AdminTypes(object):
    # partial = "partial"     # readonly access to admin panel
    standard = "standard"   # has normal access to admin panel
    full = "full"           # can create/manage standard admins
    super = "super"         # zagaran, can create/manage full admins

ALL_ADMIN_TYPES = [AdminTypes.super, AdminTypes.full, AdminTypes.standard]

class AdminStatus(object):
    active = "active"       # active
    disabled = "disabled"   # disabled


## the earliest conceivable year of birth for a user
## as of 16 January 2015, the oldest confirmed living person in the world is:
## Misao Okawa, female, of Japan, born 5 March 1898
EARLIEST_YOB = 1898

## the lowest and highest weight conceivable for a user (in pounds)
## as of 4 February 2015, the highest recorded weight of a human being is:
## 1400 lbs (John Brower Minnoch, USA, died 1983)
LOWEST_WEIGHT = 0
HIGHEST_WEIGHT = 1400