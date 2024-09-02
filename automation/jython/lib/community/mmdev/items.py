# Library for interacting with items in openhab.
import core.log
from core.exceptions import suppress
from core.jsr223.scope import itemRegistry, events
from . import types
import time


LOGGER = core.log.getLogger('ITEMS')


@core.log.log_traceback
def item_obj(item):
    return suppress(lambda: itemRegistry.getItem(item))


@core.log.log_traceback
def all_items():
    return set(str(i.getName()) for i in itemRegistry.getItems())


@core.log.log_traceback
def exists(item_name):
    return item_name in all_items()


@core.log.log_traceback
def value(item_name, default=None):
    if not exists(item_name):
        return default
    item_obj = itemRegistry.getItem(item_name)
    if item_obj is None or types.is_undefined(item_obj.state):
        return default
    try:
        return types.from_type(item_obj.state)
    except Exception as e:
        LOGGER.error('Failed to convert type for item: {}'.format(item_name))
        raise e

def item_type(item_name):
    item_obj = itemRegistry.getItem(item_name)
    return item_obj.type.split(':')[0]


def item_dimension(item_name):
    item_obj = itemRegistry.getItem(item_name)
    if ':' not in item_obj.type:
        return None
    return item_obj.type.split(':')[1]


def to_item_type(item_name, val):
    if val is None:
        return None
    item_obj = itemRegistry.getItem(item_name)
    item_type = item_obj.type.split(':')[0]

    if item_type == 'Number':
        return types.to_decimal(val)

    elif item_type == 'Dimmer':
        return types.to_percent(val)

    elif item_type == 'Switch':
        return types.to_onoff(val)

    elif item_type == 'String':
        return types.to_string(val)

    elif item_type == 'Color':
        if isinstance(val, tuple) or isinstance(val, list):
            return types.to_color(val)

        elif val is True or val is False:
            return types.to_onoff(val)

        else:
            return types.to_percent(val)
        
    else:
        raise Exception('Unsupported item type: %s' % item_obj.type)


def _apply_item(item_name, val, force, action):
    item_obj = itemRegistry.getItem(item_name)
    val = to_item_type(item_name, val)
    if force:
        core.log.log_traceback(lambda: action(item_obj, val))()
    else:
        old_val = to_item_type(item_name, value(item_name))
        if not types.is_equal(val, old_val):
            core.log.log_traceback(lambda: action(item_obj, val))()


def command(item_name, val, force=False):
    _apply_item(item_name, val, force, events.sendCommand)


def update(item_name, val, force=False):
    _apply_item(item_name, val, force, events.postUpdate)
