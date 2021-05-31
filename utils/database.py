from socket import gethostname
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from mongolia import (connect_to_database, authenticate_connection, ID_KEY,
    REQUIRED, UPDATE, CHILD_TEMPLATE, DatabaseObject, DatabaseCollection,
    set_defaults_handling, set_type_checking, AlertLevel)
from mongolia.errors import MalformedObjectError, DatabaseConflictError, DatabaseIsDownError
from mongobackup.backups import backup
from pymongo import ASCENDING
from conf.secure import (S3_BACKUP_BUCKET, S3_ACCESS_KEY_ID, S3_ACCESS_KEY,
    MONGO_PASSWORD, MONGO_USERNAME)
from utils.server import PRODUCTION
from conf.settings import BACKUPS_PATH


try:
    connect_to_database()
    try:
        authenticate_connection(MONGO_USERNAME, MONGO_PASSWORD)
    except OperationFailure as e:
        if e.message == "Authentication failed." and not PRODUCTION:
            print "\nDatabase authentication failed, proceeding because this is a non-production deployment.\n"
        else:
            print "\nDatabase authentication has failed.\n"
            raise
    set_defaults_handling(AlertLevel.error)
    set_type_checking(AlertLevel.error)
except (DatabaseIsDownError, ServerSelectionTimeoutError) as e:
    if PRODUCTION:
        raise
    else:
        print "WARNING:", e


def do_backup():
    backup(MONGO_USERNAME, MONGO_PASSWORD, BACKUPS_PATH,
           custom_prefix="%s_backup" % gethostname(),
           purge_local=30, s3_bucket=S3_BACKUP_BUCKET,
           s3_access_key_id=S3_ACCESS_KEY_ID, s3_secret_key=S3_ACCESS_KEY)


def mongo_ping(output=False):
    try:
        connect_to_database()
    except Exception:
        if output:
            print("\nMongo is down\n")
        return False
    if output:
        print("\nMongo is up\n")
    return True


def fast_live_untyped_iterator(cls, query=None, projection=None, field=None, sort_by_id=True, **kwargs):
    """
    Like class.iterator, but uses a live database connection instead of paging, and bypasses
    database object type craetion. Also supports projections.
    @param projection: list or mongo projection syntax dictionary.
    @param query: a dictionary specifying key-value pairs that the result
        must match.  If query is None, use kwargs in it's place
    @param **kwargs: used as query parameters if query is None
    """
    
    db = cls.OBJTYPE.db(cls.PATH)
    if not query:
        query = kwargs
    # construct single-field projection
    if field:
        if field == ID_KEY:
            projection = [ID_KEY]
        else:
            projection = {field: True, ID_KEY: False}
    
    if projection is None:
        results = db.find(query)
    else:
        results = db.find(query, projection=projection)
    
    if sort_by_id:
        results = results.sort(ID_KEY, ASCENDING)
    
    if field:
        return (r[field] for r in results)
    
    return results
    