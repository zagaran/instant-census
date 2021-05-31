#!/usr/bin/python

# Run this file to set up the pre-commit hook for automatic testing

import subprocess
import os
from shutil import copyfile
SUDO = None

PRE_COMMIT_HOOK = """#!/usr/bin/python
import subprocess
if subprocess.call("python manage.py import_check", shell=True): exit(1)
print("Tests passed; committing")"""

def call(cmd):
    if "sudo " in cmd:
        global SUDO
        if SUDO is None:
            if subprocess.call("sudo echo", shell=True):
                SUDO = False
                print("sudo not supported; removing from commands")
            else:
                SUDO = True
        if not SUDO:
            cmd = cmd.replace("sudo ", "")
    return subprocess.call(cmd, shell=True)


def main():
    with open(".git/hooks/pre-commit", "w") as f:
        f.write(PRE_COMMIT_HOOK)
    call("chmod +x .git/hooks/pre-commit")
    print("Git pre-commit hook successfully written")
    if "secure.py" not in os.listdir(os.getcwd() + "/conf"):
        copyfile("conf/secure.py.example", "conf/secure.py")
        print("secure.py file created")
    if "settings_override.py" not in os.listdir(os.getcwd() + "/conf"):
        with open("conf/settings_override.py", "w") as f:
            f.write("# Settings overrides go here\n")
        print("settings_override.py file created")


def ubuntu_install_mongo():
    s = "deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen\n"
    sources = False
    for line in open("/etc/apt/sources.list").readlines():
        if line == s:
            sources = True
    if not sources:
        call("sudo cat " + s + " >> /etc/apt/sources.list")
        call("sudo apt-get update")
    call("sudo apt-get install -y mongodb-10gen")
    call("sudo mongod --shutdown --dbpath /var/lib/mongodb")
    call("sudo mkdir -p /data/db")

def install_pip():
    call("sudo apt-get install -y build-essential python-dev")
    call("curl http://python-distribute.org/distribute_setup.py | sudo python")
    call("curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | sudo python")

if __name__ == "__main__":
    main()
    call("sudo pip install -r conf/requirements.txt")
