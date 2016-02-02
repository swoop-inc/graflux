import timeit

from graphite_api.config import logger

log = logger


def timed_log(msg, level='info'):
    def timed_log_decorator(func):
        def wrapper(*args, **kwargs):
            start_time = timeit.default_timer()
            func(*args, **kwargs)
            elapsed = round(timeit.default_timer() - start_time, 3)
            getattr(log, level)(msg, time=str(elapsed)+'s')
        return wrapper
    return timed_log_decorator
