from multiprocessing import Condition, Manager

shared_memory_manager = Manager()

class UserLock(object):
    """
        class_cv, active_users, responders:
            behave as private static Java variables to the Class (shared amongst all objects).
            This is because Python passes these by reference.
        responder, phonenum:
            behave as private non-static Java variables to the Class (specific to the object).
            This is because these are being re-assigned.
    """
    __class_cv = Condition()
    __active_users = shared_memory_manager.dict()
    __responders = shared_memory_manager.dict()
    __responder = True
    __phonenum = None
    
    def __init__(self, phonenum):
        self.__phonenum = phonenum
    
    def __enter__(self):
        with self.__class_cv:
            self.__responder = (self.__phonenum not in self.__responders)
            while self.__phonenum in self.__active_users:
                self.__class_cv.wait()
            self.__active_users[self.__phonenum] = True
            if self.__responder:
                self.__responders[self.__phonenum] = True
            return self
    
    def __exit__(self, type_, value, tb):
        with self.__class_cv:
            try:
                del self.__active_users[self.__phonenum]
            except KeyError:
                pass
            try:
                del self.__responders[self.__phonenum]
            except KeyError:
                pass
            self.__class_cv.notify_all()
    
    def is_responder(self):
        return self.__responder
