from functools import wraps
from contextlib import contextmanager
from core.items import remove_item, add_item
from items import exists, value, command
from prop import Prop
from core.log import log_traceback
from ruleengine import RuleEngine
from log import LOGGER
from device import Device, details, as_device, translate_camel

import time
from uuid import uuid4


class Manager(object):
    def __init__(self,
                 logger=LOGGER,
                 rule_engine=None,
                 **kwargs):
        timestamp = time.time()
        while not exists('MMDEV_BOOT'):
            if time.time() - timestamp > 60:
                try:
                    add_item('MMDEV_BOOT', item_type='Number')
                except:
                    pass
            time.sleep(0.5)

        while value('MMDEV_BOOT') is None and time.time() - timestamp < 120:
            time.sleep(0.5)

        elapsed = time.time() - timestamp
        command('MMDEV_BOOT', elapsed, force=True)

        self.__cached_devices = {}
        self.__cached_groups = {}
        self.__cached_states = {}
        self.__extra_kwargs = kwargs
        self.__logger = logger
        self.__rule_engine = rule_engine

        if self.__rule_engine is None:
            self.__rule_engine = RuleEngine(
                logger=logger
            )

    @log_traceback
    def device_for(self, device_class, room_name=None, device_name=None, parent=None, **kwargs):
        if device_name is None:
            device_name = uuid4().hex

        if room_name is None:
            room_name = uuid4().hex

        device_collection, class_name = details(device_class)
        if parent is None:
            full_name = 'MMDEV_%s_%s_%s_%s' % (
                device_collection, class_name,
                room_name.replace(' ', '') if room_name is not None else '',
                device_name.replace(' ', '')
            )
        else:
            full_name = '%s_%s_%s_%s' % (
                parent.item_base, device_collection, class_name,
                device_name.replace(' ', '')
            )

        if full_name in self.__cached_devices:
            return self.__cached_devices[full_name]

        d=Device(
            device_class=device_class,
            device_name=device_name,
            room_name=room_name,
            rule_engine=self.__rule_engine,
            item_base=full_name,
            logger=self.__logger
        )

        cached_device = device_class(device=d, **kwargs)
        self.__cached_devices[full_name] = cached_device
        return cached_device

    @log_traceback
    def state_for(self, state_type, state_name, parent=None, **kwargs):
        full_name = '%s_State_%s' % (parent.item_base if parent else 'MMDEV', state_name)
        if full_name in self.__cached_states:
            return self.__cached_states[full_name]

        def default(key, value):
            if key not in kwargs:
                kwargs[key] = value

        default('rule_engine', self.__rule_engine)
        default('logger', self.__logger)
        default('property_name', state_name)

        cached = Prop(state_type, full_name, **kwargs)
        self.__cached_states[full_name] = cached
        return cached

    @log_traceback
    def group_for(self, group_name, metadata=None, logger=None, parent=None):
        group_item = '%s_Group_%s' % (parent.item_base if parent else 'MMDEV', group_name)
        if group_item in self.__cached_groups:
            return self.__cached_groups[group_item]
        if logger is None:
            logger=self.__logger
        group = Prop(
            set, group_item,
            metadata=metadata,
            logger=logger,
            rule_engine=self.rule_engine,
            property_name=group_name
        )
        self.__cached_groups[group_item] = group
        return group

    def ephemeral_for(self, device_name, room_name=None):

        @as_device(
            collection='Ephemeral',
            name='Ephemeral'
        )
        def Ephemeral(device):
            return {}

        class EphemeralDevice(object):
            def __init__(*args, **kwargs):
                self, args = args[0], args[1:]
                self.__device = Device(*args, **kwargs)
            
            def property(*args, **kwargs):
                self, args = args[0], args[1:]
                return self.__device.property(*args, **kwargs)

            @log_traceback
            def __getattr__(self, attrib):
                for p, v in self.__device.properties.items():
                    if attrib in {p, translate_camel(p)}:
                        return v
                raise AttributeError()

        return EphemeralDevice(
            room_name=room_name, 
            device_class=Ephemeral, 
            device_name=device_name, 
            rule_engine=self.rule_engine
        )

    @property
    def rule_engine(self):
        return self.__rule_engine

    @property
    def logger(self):
        return self.__logger
