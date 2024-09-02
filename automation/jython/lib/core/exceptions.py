from functools import wraps
from community.mmdev.log import LOGGER

from core.kwargs import parser as kwargs_parser


class Suppressor(object):

    def __init__(self, exceptions):
        self.__exceptions = exceptions

    def __call__(self, function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            return suppress(
                lambda: function(
                    *args, **kwargs
                ),
                exceptions=self.__exceptions
            )
        return wrapper

    def __enter__(self):
        pass

    def __exit__(self, t, e, tb):
        try:
            @suppress(self.__exceptions)
            def raiser():
                raise e
            wrapper()
            return True
        except:
            return False


def suppress(*args, **kwargs):
    with kwargs_parser(**kwargs) as parser:
        exceptions = parser.optional('exceptions', default={Exception})

    if len(args) > 1:
        raise Exception('Invalid number of arguments, must be 1 or 0.')
    elif len(args) == 1:
        try:
            return args[0]()
        except Exception as e:
            if not any(isinstance(e, ex) for ex in exceptions):
                raise e
    else:
        return Suppressor(exceptions)
