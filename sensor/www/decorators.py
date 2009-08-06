# danv - some decorators for restricting access to URLs

import web, shelve, datetime

# restricted URL's require this key to be passed in as a GET or
# POST param.
SECRET_KEY='7787855982'

# use the @restricted decorator to protect sensitive URLs
def restricted(view):
    def _wrapper(*args, **kw):
        params = web.input(key=None)
        if params.key != SECRET_KEY:
            return '!restricted URL - for VHS members only'
        return view(*args, **kw)
    return _wrapper

SHELF_PATH = '/tmp/sensor.shelf'
def throttled(timeout=10, everyone=True):
    """
    Throttle access to a view

    timeout -- minimum wait time between responses
    everyone -- if True, apply throttling to authorized clients as well
    """

    def _decorator(view):
        def _wrapper(*args, **kw):
            params = web.input(key=None)

            if params.key != SECRET_KEY or everyone:
                # check to see if a recent response is available
                shelf = shelve.open(SHELF_PATH)

                now = datetime.datetime.now()
                if shelf.has_key(view.__name__):
                    (timestamp, previous_response) = shelf[view.__name__]
                    if (now - timestamp).seconds <= timeout:
                        return previous_response

                response = view(*args, **kw)
                shelf[view.__name__] = (now, response)
                shelf.sync()
                return response

            else:
                # authorized clients - no worries!
                return view(*args, **kw)

        return _wrapper

    return _decorator


