from inspect import getargspec
from uuid import uuid4

from utils.logging import log_error


ACTIONS = {}
DYNAMIC_PARAMS = ["user", "parser_return", "execution_state", "resend", "delay"]


class ActionConfig(object):
    @staticmethod
    def do_action(action_config, user, parser_return=None, execution_state=[],
                  resend=False, delay=True):
        passed_dynamic_params = {"user": user, "parser_return": parser_return,
                                 "execution_state": execution_state,
                                 "resend": resend, "delay": delay}
        action_name = action_config["action_name"]
        params = dict(action_config["params"])
        dynamic_params = ActionConfig.get_dynamic_params(action_name)
        for param_name in passed_dynamic_params:
            if param_name in dynamic_params:
                params[param_name] = passed_dynamic_params[param_name]
        return ACTIONS[action_name]["function"](**params)
    
    @staticmethod
    def get_dynamic_params(action_name):
        return ACTIONS[action_name]["dynamic_params"]
    
    @staticmethod
    def get_static_params(action_name):
        return ACTIONS[action_name]["static_params"]
    
    @staticmethod
    def create_config(action_name, params_dict=None, existing_id=None, **params):
        static_params = ActionConfig.get_static_params(action_name)
        if params_dict is not None:
            params = params_dict
        for key in DYNAMIC_PARAMS:
            if key in params:
                raise Exception("% is reserved dynamic keyword, yet appears in params" % (key))
        for key in static_params:
            if key not in params:
                raise Exception("%s missing in config for action %s" % (key, action_name))
        for key in params:
            if key not in static_params:
                raise Exception("Key %s is invalid for action %s" % (key, action_name))
        if existing_id is not None:
            _id = existing_id
        elif 'database_id' in params:
            _id = params['database_id']
        else:
            _id = uuid4()
        return {"action_name": action_name, "params": params, "action_id": _id}


def Action(name):
    """ Registers any function with this decorator onto the ACTIONS dict
        under the key of it's name; this decorator also registers the
        parameters that the function takes, sorting them under
        static params (those passed in from the database configuration) and/or
        dymanic params (those passed in at run time); dynamic params
        are those from the list DYNAMIC_PARAMS.
        
        Additionally adds a try-except block around the entire function
        call to prevent bad database config from breaking the codebase.
        
        NOTE: Any function with the @Action(name) decorator must
        still be imported by the project to be reachable."""
    
    class ActionDecorator(object):
        def __init__(self, fn):
            self.fn = fn
            static_params = [arg for arg in getargspec(fn)[0] if arg not in DYNAMIC_PARAMS]
            dynamic_params = [arg for arg in getargspec(fn)[0] if arg in DYNAMIC_PARAMS]
            ACTIONS[name] = {"function": fn, "static_params": static_params,
                             "dynamic_params": dynamic_params}
        
        def __call__(self, *args, **kwargs):
            try:
                return self.fn(*args, **kwargs)
            except Exception as e:
                log_error(e, 'Error in action ' + name)
    
    return ActionDecorator