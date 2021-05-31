from utils.database import DatabaseObject, DatabaseCollection, ID_KEY
from utils.server import hostname_of_server

class Server(DatabaseObject):
    PATH = "backbone.servers"
    DEFAULTS = {"name": "unknown"}
    
    @classmethod
    def get_name(cls, addr):
        name = hostname_of_server(addr)
        db_entry = cls(addr)
        if name and db_entry:
            db_entry["name"] = name
            db_entry.save()
            return name
        elif name and not db_entry:
            cls.create({ID_KEY: addr, "name": name})
            return name
        elif not name and db_entry:
            return db_entry["name"]
        return "unknown"

class Servers(DatabaseCollection):
    OBJTYPE = Server
