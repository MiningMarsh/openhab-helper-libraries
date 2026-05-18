import threading


class Timer(threading.Timer):
    @staticmethod
    def createTimeout(duration, callback, args=[], kwargs={}, old_timer=None):
        if old_timer != None:
            old_timer.cancel()
        timer = Timer(duration, callback, args, kwargs)
        timer.start()
        return timer

    @staticmethod
    def create(duration, callback, args=[], kwargs={}, old_timer=None):
        return Timer.createTimeout(
            duration, callback,
            args=args, kwargs=kwargs,
            old_timer=old_timer
        )


def create(duration, callback, args=[], kwargs={}, old_timer=None):
    return Timer.createTimeout(
        duration, callback,
        args=args, kwargs=kwargs,
        old_timer=old_timer
    )
