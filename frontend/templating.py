from flask import render_template, jsonify
import functools

def extend_template_args(args): pass

class Template(object):
    def __init__(self, template=None, path=None, **template_args):
        self.template = template or "base.html"
        self.args = template_args
        self.args['active_path'] = path

    def set_title(self, title):
        self.args['title'] = title

    def set_path(self, path):
        self.args['active_path'] = path

    def render(self, **args):
        self.args.update(args)
        extend_template_args(self.args)
        return render_template(self.template, **self.args)


def template(template=None, path=None, argify=False, **settings):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            t = Template(template=template, path=path, **settings)
            if argify:
                output = f(t, *args, **kwargs)
            else:
                output = f(*args, **kwargs)
            if isinstance(output, dict):
                if "status_code" in output:
                    status_code = output.pop("status_code")
                    return t.render(**output), status_code
                return t.render(**output)
            elif output is None:
                return t.render()
            else:
                return output
        return wrapper
    return decorator


base = functools.partial(template, template="base.html")
