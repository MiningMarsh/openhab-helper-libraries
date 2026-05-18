import uuid
import random
from functools import wraps


from scope import RuleSupport
import scope
import openhab
import openhab.triggers
from scope import RuleSupport


from .utils import sanitize, suppress


class Rule:
    def __init__(self, callback):
        if isinstance(callback, Rule):
            callback = callback.passthrough
        self.__callback = callback
        self.__updates = {}
        self.__commands = {}
        self.__changes = {}
        self.__triggers = {}
        self.__timers = set()
        self.__trace = False
        self.__pass_context = False
        self.__null_context = False
        self.__tracer = None

    def __call__(self, *args, **kwargs):
        return self.__callback(*args, **kwargs)

    @property
    def pass_context(self):
        return self.__pass_context

    def enable_pass_context(self):
        self.__pass_context = True

    @property
    def null_context(self):
        return self.__null_context

    def enable_null_context(self):
        self.__null_context = True

    @property
    def tracing(self):
        return self.__tracer

    def enable_tracing(self, logger):
        self.__tracer = logger

    def on_update(self, item, callback):
        self.__updates[item] = callback

    def on_command(self, item, callback):
        self.__commands[item] = callback

    def on_change(self, item, callback):
        self.__changes[item] = callback

    def on_timer(self, cron):
        self.__timers.add(cron)

    def on_trigger(self, channel, callback):
        self.__triggers[channel] = callback

    @property
    def passthrough(self):
        return self.__callback

    def callback(self, module, event):
        if self.__tracer:
            self.__tracer(f'Event: {event["event"]}')
        if 'ItemCommandEvent' in str(type(event['event'])):
            item = event['event'].getItemName()
            return self.__commands[item](event)
        elif 'ItemStateChangedEvent' in str(type(event['event'])):
            item = event['event'].getItemName()
            return self.__changes[item](event)
        elif 'ItemStateUpdateeEvent' in str(type(event['event'])):
            item = event['event'].getItemName()
            return self.__updates[item](event)
        elif 'ChannelTriggeredEvent' in str(type(event['event'])):
            channel = event['event'].getChannel()
            return self.__triggers[channel](event)
        elif 'TimerEvent' in str(type(event['event'])):
            return self.__callback()

    def register(self):
        def wrapper(module, event):
            return self.callback(module, event)
        for item in self.__commands.keys():
            wrapper = openhab.triggers.when(f'Item {item} received command') (wrapper)
        for item in self.__updates.keys():
            wrapper = openhab.triggers.when(f'Item {item} received update') (wrapper)
        for item in self.__changes.keys():
            wrapper = openhab.triggers.when(f'Item {item} changed') (wrapper)
        for timer in self.__timers:
            wrapper = openhab.triggers.when(f'Time cron {timer}') (wrapper)

        return openhab.rule(
            'mmdev-%s' % (str(uuid.uuid4())),
            description='Auto-generated rule created by the `mmdev` library',
            tags=['mmdev'],
            runtime_measurement=self.__tracer is not None
        ) (wrapper)


__SECONDS_INDEX = random.randint(0, 59)


def register(r):
    r.register()
    return r.passthrough


def every_second(function):
    if isinstance(function, Rule):
        r = function
    else:
        r = Rule(function)
    r.on_timer('* * * ? * * *')
    return r


def loop(function):
    global __SECONDS_INDEX
    __SECONDS_INDEX = (__SECONDS_INDEX + 13) % 60

    if isinstance(function, Rule):
        r = function
    else:
        r = Rule(function)
    r.on_timer(f'{__SECONDS_INDEX} * * ? * * *')
    return r


def every_day(hour, minute):
    def decorator(function):
        if isinstance(function, Rule):
            r = function
        else:
            r = Rule(function)
        r.on_timer(f'0 {minute} {hour} ? * * *')
        return r
    return decorator


def on_weekdays(hour, minute):
    def decorator(function):
        if isinstance(function, Rule):
            r = function
        else:
            r = Rule(function)
        r.on_timer(f'0 {minute} {hour} ? * MON,TUE,WED,THU,FRI *')
        return r
    return decorator


def on_weekends(hour, minute):
    def decorator(function):
        if isinstance(function, Rule):
            r = function
        else:
            r = Rule(function)
        r.on_timer(f'0 {minute} {hour} ? * SAT,SUN *')
        return r
    return decorator
        

def on_change(item):
    def decorator(function):
        if isinstance(function, Rule):
            r = function
        else:
            r = Rule(function)

        @wraps(function)
        def wrapper(event):
            if r.pass_context:
                old_value = suppress(lambda: sanitize(event['oldState']))
                value = suppress(lambda: sanitize(event['newState']))
                if r.null_context or all(v is not None for v in (old_value, value)):
                    function(old_value, value)
            else:
                return function()

        r.on_change(item, wrapper)
        return r
    return decorator


def on_command(item):
    def decorator(function):
        if isinstance(function, Rule):
            r = function
        else:
            r = Rule(function)

        @wraps(function)
        def wrapper(event):
            if r.pass_context:
                command = suppress(lambda: sanitize(event['command']))
                if r.null_context or command is not None:
                    function(command)
            else:
                return function()

        r.on_command(item, wrapper)
        return r
    return decorator


def on_update(item):
    def decorator(function):
        if isinstance(callback, Rule):
            r = callback
        else:
            r = Rule(callback)

        @wraps(function)
        def wrapper(event):
            if r.pass_context:
                update = suppress(lambda: sanitize(event['update']))
                if r.null_context or update is not None:
                    function(update)
            else:
                return function()

        r.on_update(item, wrapper)
        return r
    return decorator


def on_trigger(channel):
    def decorator(function):
        if isinstance(function, Rule):
            r = function
        else:
            r = Rule(function)

        def wrapper(event):
            if r.pass_context:
                channel = suppress(lambda: str(event['event'].getChannel()))
                value = suppress(lambda: event['event'].getEvent())
                if r.null_context or value is not None:
                    function(channel, value)
            else:
                return function()

        r.on_trigger(channel, wrapper)
        return r
    return decorator


def trace_execution(logger):
    def decorator(function):
        if isinstance(function, Rule):
            r = function
        else:
            r = Rule(function)
        r.enable_tracing(logger)
        return r
    return decorator


def pass_context(function):
    if isinstance(function, Rule):
        r = function
    else:
        r = Rule(function)
    r.enable_pass_context()
    return r


def null_context(function):
    if isinstance(function, Rule):
        r = function
    else:
        r = Rule(function)
    r.enable_null_context()
    return r
