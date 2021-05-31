from utils.database import CHILD_TEMPLATE, DatabaseObject, DatabaseCollection

def all_children(cls):
    import app  # @UnusedImport to get scope of codebase
    import cron  # @UnusedImport to get scope of codebase
    
    def inner(_class):
        children = _class.__subclasses__()
        if not children:
            return []
        return children + [grandchild for child in children for grandchild in inner(child)]
    return inner(cls)


def all_databases():
    return [child for child in all_children(DatabaseObject) if child.PATH != CHILD_TEMPLATE]

def all_collections():
    return [child for child in all_children(DatabaseCollection) if child.__objtype__.__db__ != CHILD_TEMPLATE]

def all_database_paths():
    return set(child.PATH for child in all_databases())
