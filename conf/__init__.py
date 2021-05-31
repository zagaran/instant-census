try:
    from secure import SENTRY_DSN, JS_SENTRY_DSN
except ImportError:
     print "\nSENTRY_DSN and JS_SENTRY_DSN are now required variables. " \
           "If you want to run without sentry you can use the dummy values secure.py.example.\n"