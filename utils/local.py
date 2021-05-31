import subprocess
from utils.server import development_only


@development_only
def delete_pyc_files():
    subprocess.call("find . -name '*.pyc' -delete", shell=True)


@development_only
def untracked_file_check():
    status = subprocess.Popen("git status --porcelain", shell=True, stdout=subprocess.PIPE).communicate()[0]
    for line in status.split("\n"):
        if line.startswith("??"):
            print("ERROR: UN-TRACKED FILE(S) IN GIT REPOSITORY")
            exit(1)
