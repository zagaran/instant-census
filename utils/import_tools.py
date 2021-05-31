import os
import glob

def import_current_directory(current_file):
    '''
    USE WITH CAUTION

    This beast does dynamic imports of all files based on the current
    directory. Currently does not capture subdirectories
    
    USAGE in top of __init__.py:

    from utils.import_tools import import_current_directory
    import_current_directory(__file__)


    '''
    path = os.path.dirname(current_file)
    modules = [os.path.basename(f)[:-3] for f in glob.glob(path + "/*.py")
               if not os.path.basename(f).startswith('_')]
    stripped_path = os.path.relpath(path).replace('/', '.')
    for module in modules:
        __import__(stripped_path, fromlist=[module])
