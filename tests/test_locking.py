from datetime import datetime, timedelta
from utils.concurency import UserLock
from threading import Thread
from multiprocessing.process import Process
from time import sleep
from timeit import default_timer

def test_user_lock():
    hold_user_lock(5)
    run_threads([Thread(target=hold_user_lock, args=[i]) for i in range(5)])
    run_threads([Thread(target=hold_user_lock, args=[5]) for _ in range(5)])
    run_threads([Process(target=hold_user_lock, args=[i]) for i in range(5)])
    run_threads([Process(target=hold_user_lock, args=[5]) for _ in range(5)])

def hold_user_lock(i, sleep_time=0):
    with UserLock(i):
        _unused = i ** 10
        if sleep_time:
            sleep(sleep_time)

def run_threads(threads):
    for t in threads:
        t.start()
    for t in threads:
        t.join()

def full_lock_drill():
    """ Takes time due to sleep statements and is missing assertions.
        Do not run in tests proper. """
    print "Beginning locking test"
    start = default_timer()
    run_threads([Thread(target=hold_user_lock, args=[i, 10]) for i in range(5)])
    end = default_timer()
    print "Non-exclusive threads; runtime should be about 10:", end - start
    start = default_timer()
    run_threads([Thread(target=hold_user_lock, args=[5, 10]) for _ in range(5)])
    end = default_timer()
    print "Exclusive threads; runtime should be about 50:", end - start
    start = default_timer()
    run_threads([Process(target=hold_user_lock, args=[i, 10]) for i in range(5)])
    end = default_timer()
    print "Non-exclusive processes; runtime should be about 10:", end - start
    start = default_timer()
    run_threads([Process(target=hold_user_lock, args=[0, 10]) for _ in range(5)])
    end = default_timer()
    print "Exclusive processes; runtime should be about 50:", end - start
