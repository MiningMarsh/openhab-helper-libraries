# Library for interacting with items in openhab.

import core.log
from core.jsr223.scope import items, itemRegistry, events
from . import types


ITEMS=items


def items():
    return sorted(ITEMS.keys())


def item_exists(item_name):
    return item_name in items()


def item(item_name, default=None):
    if not item_exists(item_name):
        return default
    item_obj = itemRegistry.getItem(item_name)
    if default is None:
        return types.from_type(item_obj.state)
    elif types.is_undefined(item_obj.state):
        update(item_name, default, force=True)
        return default
    else:
        return types.from_type(item_obj.state)


def item_type(item_name):
    item_obj = itemRegistry.getItem(item_name)
    return item_obj.type.split(':')[0]


def to_item_type(item_name, value):
    if value is None:
        return None
    item_obj = itemRegistry.getItem(item_name)
    state = item_obj.getState()
    item_type = item_obj.type.split(':')[0]

    if item_type == 'Number':
        return types.to_decimal(value)

    elif item_type == 'Dimmer':
        return types.to_percent(value)

    elif item_type == 'Switch':
        return types.to_onoff(value)

    elif item_type == 'Color':
        if isinstance(value, tuple) or isinstance(value, list):
            return types.to_color(value)

        elif value is True or value is False:
            return types.to_onoff(value)

        else:
            return types.to_percent(value)
        
    else:
        raise Exception('Unsupported item type: %s' % item_obj.type)


def _apply_item(item_name, value, force, action):
    item_obj = itemRegistry.getItem(item_name)
    value = to_item_type(item_name, value)
    if force:
        core.log.log_traceback(lambda: action(item_obj, value))()
    else:
        old_value = to_item_type(item_name, item(item_name))
        if not types.is_equal(value, old_value):
            core.log.log_traceback(lambda: action(item_obj, value))()


def command(item_name, value, force=False):
    _apply_item(item_name, value, force, events.sendCommand)


def update(item_name, value, force=False):
    _apply_item(item_name, value, force, events.postUpdate)
