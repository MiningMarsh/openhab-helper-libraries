import core.date
from java.util import UUID

try:
    from core.actions import Timer
    from core.actions import ScriptExecution
except:
    Timer = None
    ScriptExecution = None


_TIMERS = {
}


class _JythonTimer(object):

    def __init__(self, timer, callback):
        self.__timer = timer
        self.__callback = callback

    @property
    def callback(self):
        return self.__callback

    def get_callback(self):
        return self.__callback

    @property
    def active(self):
        return self.__timer.isActive()

    def is_active(self):
        return self.__timer.isActive()

    @property
    def terminated(self):
        return self.__timer.hasTerminated()

    def has_teriminated(self):
        return self.__timer.hasTerminated()

    @property
    def execution_time(self):
        return self.__timer.getExectionTime()

    def get_execution_time(self):
        return self.__timer.getExectionTime()

    @property
    def cancelled(self):
        return self.__timer.isCancelled()

    def is_cancalled(self):
        return self.__timer.isCancelled()

    @property
    def running(self):
        return self.__timer.isRunning()

    def is_running(self):
        return self.__timer.isRunning()

    def cancel(self):
        return self.__timer.cancel()

    def rescheduled(date):
        date = to_java_zoneddatetime(date)
        return self.__timer.reschedule(date)

    @property
    def timer(self):
        return self.__timer

    def get_timer(self):
        return self.__timer
    

def available():
    return Timer is not None and ScriptExecution is not None


def require():
    if not available():
        raise Exception('A timer function has been called, but the environment signals no timer support is available!')


def generate_name():
    return 'ScriptExecutionTimer-%s' % str(UUID.randomUUID())


def _flush(name=None):
    global _TIMERS
    new_timers = {}
    for name, timer in _TIMERS.items():
        if timer.cancelled or timer.terminated or not timer.active:
            new_timers[name] = timer
    _TIMERS = new_timers
    if name is not None and name in _TIMERS:
        return _TIMERS[name]


def create(date, callback, name=None, arg=None):
    global _TIMERS
    require()
    if name is None:
        name = generate_name()

    if _flush(name):
        raise Exception('Cannot create duplicate timers!')

    date = core.date.to_java_zoneddatetime(date)
    if arg is None:
        timer = ScriptExecution.createTimer(name, date, callback)
    else:
        timer = ScriptExecution.createTimerWithArgument(name, date, arg, callback)
    timer = _JythonTimer(timer, callback)
    _TIMERS[name] = timer

    return timer


def exists(name):
    require()
    return _flush(name) is not None


def get(name):
    require()
    return _flush(name)


def all():
    results = []
    for key in _TIMERS.keys():
        if _flush(key):
            results.append(key)
    return results


def cancel(name):
    require()
    timer = _flush(name)
    if timer:
        timer.cancel()
        return timer


def reschedule(name, date):
    require()
    timer = _flush(name)
    if timer:
        timer.reschedule(date)
        return timer
