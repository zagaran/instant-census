from collections import defaultdict
from datetime import datetime
from inspect import getframeinfo, stack
from os.path import relpath

import mongolia
from pymongo import ASCENDING, DESCENDING, HASHED


def profileit(func):
    """ wrap a function with this decorator to create an automatic cprofile of it. """
    import cProfile
    def wrapper(*args, **kwargs):
        fn_name = func.__name__
        print "profiling", fn_name, "..."
        
        prof = cProfile.Profile()
        start = datetime.now()
        retval = prof.runcall(func, *args, **kwargs)
        end = datetime.now()
        
        # you can stick print statements of the profile here:
        # prof.print_stats()
        
        print(fn_name, "took %s seconds to run.", (end - start).total_seconds())
        print "creating %s.profile", fn_name
        prof.dump_stats(fn_name + ".profile")
        return retval
    return wrapper
    

class timer_class():
    """ This is a simple class that is at the heart of the p() function declared below.
        This class consists of a datetime timer and a single function to access and advance it. """
    start = None
    def get_timer(self):
        if self.start == None:
            self.start = datetime.now()
            print "profiling start...",
            return self.start
        else:
            ret = self.start
            self.start = datetime.now()
            return ret

# we use a defaultdict of timers to allow an arbitrary number of such timers.
timers = defaultdict(timer_class)

def p(timer_label=0):
    """ Handy little function that prints the file name line number it was called on and the
        amount of time since the function was last called.
        If you provide a label (anything with a string representation) that will be printed
        along with the time information.
        
    Examples:
         No parameters (source line numbers present for clarity):
            [app.py:65] p()
            [app.py:66] sleep(0.403)
            [app.py:67] p()
         This example's output:
            app.py:65 -- 0 -- profiling start...
            app.py:67 -- 0 -- 0.405514
         
         The second statement shows that it took just over the 0.403 time of the sleep statement
         to process between the two p calls.
         
         With parameters (source line numbers present for clarity):
             [app.py:65] p()
             [app.py:66] sleep(0.403)
             [app.py:67] p(1)
             [app.py:68] sleep(0.321)
             [app.py:69] p(1)
             [app.py:70] p()
         This example's output:
             app.py:65 -- 0 -- profiling start...
             app.py:67 -- 1 -- profiling start...
             app.py:69 -- 1 -- 0.32679
             app.py:70 -- 0 -- 0.731086
         Note that the labels are different for the middle two print statements.
         In this way you can interleave timers with any label you want and time arbitrary,
         overlapping subsections of code.  In this case I have two timers, one timed the
         whole process and one timed only the second timer.
    """
    caller = getframeinfo(stack()[1][0])
    print "%s:%d -- %s --" % (relpath(caller.filename), caller.lineno, timer_label),
    elapsed_time = (datetime.now() - timers[timer_label].get_timer()).total_seconds()
    # the first call to get_timer results in a negative elapsed time, so we can skip it.
    if elapsed_time > 0:
        print elapsed_time
    else:
        print


def enumerfile(iterable, label="enumerfile", count=1000):
    """ This is an enumerate function, but it prints the time for every 1000 things you have
        iterated over.
        You can set the iteration count to print at, and the label (defaults to "enumerfile") """
    for i, ret in enumerate(iterable):
        if i % count == 0:
            p(label)
        yield ret



##########################################################
################ Mongo Index Utilities ###################

INDEX_TYPE_MAPPING = {
    str(ASCENDING): "sorted -- ascending index",
    str(DESCENDING): "sorted -- descending index",
    # the pymongo HASHED variable is not '2', but the value appears to be 2 on some versions of mongo?
    "2": "unknown index type (probably hashed, '2')",
}

def _get_index_type(index_type_value):
    """ index typing is obnoxious, helper function """
    index_type_key = str(index_type_value)
    if index_type_key in INDEX_TYPE_MAPPING:
        return INDEX_TYPE_MAPPING[index_type_key]
    return "unknown index type: '%s'" % str(index_type_key)

def print_collection_indexes():
    database_connection = mongolia.mongo_connection.CONNECTION.get_connection()
    for db_name in database_connection.database_names():
        db = database_connection[db_name]
        title = "========== '%s' database ==========" % db_name
        print "\n", "="*len(title), "\n", title, "\n", "="*len(title)
        for collection_name in db.collection_names():
            collection = db[collection_name]
            print "\n'%s' collection..." % collection_name
            count = 0
            
            # 'stuff' is a really gross dictionary, the key 'ns' stands for namespace.
            for index_name, stuff in collection.index_information().iteritems():
                # this index is auto-index for the id field of the collection.
                if index_name == "_id_":
                    continue
                count += 1
                
                # get the information we care about...
                field_name, index_type = stuff['key'][0]
                index_type = _get_index_type(index_type)
                
                # print stuff legibly
                print "  field name:", field_name
                print "    index name:", index_name
                print "    type:", index_type
            if not count:
                print "  no indexes..."


def create_indexes():
    """
    The following is the relevant output of print_db_indexes from the sixt deployment:

    tracking.control_messages: time
        name:'time_1' (sorted - ascending index)
    
    tracking.schedule_execution: schedule_id
        name:'schedule_id_1' (sorted - ascending index)
    tracking.schedule_execution: user_id
        name:'user_id_1' (sorted - ascending index)
        
    tracking.texts: time
        name:'time_1' (sorted - ascending index)
        
    tracking.users: phonenum
        name:'phonenum_1' (sorted - ascending index)
    tracking.users: cohort_id
        name:'cohort_id_1' (sorted - ascending index)
    tracking.users: ic_number
        name:'ic_number_1' (sorted - ascending index)

    """
    # connect to pymongo
    database_connection = mongolia.mongo_connection.CONNECTION.get_connection()
    tracking = database_connection.get_database('tracking')
    
    # get the collections, you can print
    texts_collection = tracking.get_collection("texts")
    control_messages_collection = tracking.get_collection("control_messages")
    users_collection = tracking.get_collection("users")
    schedule_execution_collection = tracking.get_collection("schedule_execution")
    
    # TODO: there is no documentaton of why each index was created, document.
    
    # print "creating in index for user_id on texts_collection"
    # texts_collection.create_index([("user_id", ASCENDING)], background=True)
    print "creating index for time on texts_collection"
    texts_collection.create_index([("time", ASCENDING)], background=True)

    print "creating index for time on control_messages_collection"
    control_messages_collection.create_index([("time", ASCENDING)], background=True)

    print "creating index for phonenum on users_collection"
    users_collection.create_index([("phonenum", ASCENDING)], background=True)
    print "creating index for cohort_id on users_collection"
    users_collection.create_index([("cohort_id", ASCENDING)], background=True)
    print "creating index for ic_number on users_collection"
    users_collection.create_index([("ic_number", ASCENDING)], background=True)
    
    print "creating index for user_id on schedule_execution_collection"
    schedule_execution_collection.create_index([("user_id", ASCENDING)], background=True)
    print "creating index for schedule_id on schedule_execution_collection"
    schedule_execution_collection.create_index([("schedule_id", ASCENDING)], background=True)
    
    

## The following code is how to structure a drop index command
# database_connection = mongolia.mongo_connection.CONNECTION.get_connection()
# print database_connection.list_database_names()
# tracking = database_connection.get_database('tracking')
# texts_collection.drop_index('user_id_1')
