#!/usr/bin/python

""" DO NOT IMPORT ANYTHING HIGHER UP THAN UTILS IN THE GLOBAL SCOPE.
    DOING SO WILL BREAK SERVER SETUP """

import sys
import unittest2 as unittest
from IPython import start_ipython

from utils.local import untracked_file_check, delete_pyc_files
from utils.server import TEST_RUN

COMMANDS = {"shell": "runs an ipython shell to interact with the database",
            "import_check": "ensures that code is good to commit",
            "test": "runs the regular test suite",
            "full_tests": "runs a lengthy test suite",
            "ping": "checks if the database is up or down",
            "setup": "args: customer_name [admin_emalis]; needs sudo",
            "deploy_check": "checks if the system is safe to deploy",
            "make_customer": ""}

def project_import_check():
    import app  # @UnusedImport to ensure no syntax errors in the codebase
    import cron  # @UnusedImport to ensure no syntax errors in the codebase
    import utils.database  # @UnusedImport to ensure database connection

def regular_test_suite():
    global TEST_RUN
    TEST_RUN = True
    project_import_check()
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(".")

    #to run individual tests, comment out the line above (test_loader.discoverer) and use the following:
    #from tests.test_cohort_dashboard import TestCohortsDashboard
    #from tests.test_integration import TestIntegration
    #from tests.test_status_change_messages import TestStatusChangeMessages
    #test_suite = unittest.TestSuite()
    #test_suite.addTest(TestIntegration("test_copied_schedule"))

    test_runner = unittest.TextTestRunner(buffer=True)
    test_runner.run(test_suite)


def full_test_suite():
    from tests.test_locking import full_lock_drill
    full_lock_drill()
    regular_test_suite()


if __name__ == "__main__":
    delete_pyc_files()
    if len(sys.argv) <= 1 or sys.argv[1] not in COMMANDS:
        print "Usage: python manage.py COMMAND"
        print "\nCOMMAND takes one of the following options:\n"
        for k, v in COMMANDS.items():
            print "%s: %s" % (k, v)
        print
    elif sys.argv[1] == "shell":
        start_ipython(argv=["-i", "supertools/terminal.py"])
    elif sys.argv[1] == "ping":
        from utils.database import mongo_ping
        mongo_ping(output=True)
    elif sys.argv[1] == "import_check":
        untracked_file_check()
        project_import_check()
    elif sys.argv[1] == "test":
        print "\nWarning: Settings in settings_override.py should be disabled prior to running tests.\n"
        regular_test_suite()
    elif sys.argv[1] == "full_tests":
        print "\nWarning: Settings in settings_override.py should be disabled prior to running tests.\n"
        full_test_suite()
    elif sys.argv[1] == "deploy_check":
        from supertools.cron_status import safe_to_deploy
        if not safe_to_deploy():
            raise Exception("Error: hourly cron may be running; it is not currently safe to deploy")
        print "Deploy check passed"
    elif sys.argv[1] == "setup":
        if len(sys.argv) <= 2:
            print "Usage: setup customer_name [admin_emalis]"
            exit(1)
        from supertools.setup import do_setup
        do_setup(sys.argv[2], sys.argv[3:])
    else:
        raise Exception("Not Implemented")
