from utils.codes import random_string


def do_setup(customer_name, admin_emails):
    from mongolia import add_superuser, ID_KEY
    from conf.secure import MONGO_USERNAME, MONGO_PASSWORD
    add_superuser(MONGO_USERNAME, MONGO_PASSWORD)
    
    import utils.database  # @UnusedImport to connect to database
    from database.backbone.cohorts import Customer
    from database.tracking.admins import Admin
    customer = Customer.make_customer(customer_name)
    Admin.get_internal_super_admin().update({"customer_id": customer[ID_KEY]})
    for email in admin_emails:
        Admin.make_admin(email, random_string(), customer[ID_KEY])
