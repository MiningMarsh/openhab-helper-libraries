from uuid import uuid4


from functools import wraps
from contextlib import contextmanager
from mmdev.prop import Prop
import mmdev.rules as rules
from mmdev.device import Device, details, as_device, translate_camel, item_base


class Manager(object):
    def __init__(self, **kwargs):
        self.__cached_devices = {}
        self.__cached_groups = {}
        self.__cached_states = {}
        self.__extra_kwargs = kwargs

    def device_for(self, device_class, room_name=None, device_name=None, parent=None, **kwargs):
        if device_name is None:
            device_name = uuid4().hex

        if room_name is None:
            room_name = uuid4().hex

        device_collection, class_name = details(device_class)
        full_name = item_base(
            device_collection,
            class_name,
            room_name,
            device_name,
            parent=parent
        )

        if full_name in self.__cached_devices:
            return self.__cached_devices[full_name]

        d=Device(
            device_class=device_class,
            device_name=device_name,
            room_name=room_name,
            item_base=full_name
        )

        cached_device = device_class(device=d, **kwargs)
        self.__cached_devices[full_name] = cached_device
        return cached_device

    def state_for(self, state_type, state_name, parent=None, **kwargs):
        full_name = '%s_State_%s' % (parent.item_base if parent else 'MMDEV', state_name)
        if full_name in self.__cached_states:
            return self.__cached_states[full_name]

        def default(key, value):
            if key not in kwargs:
                kwargs[key] = value

        default('property_name', state_name)

        cached = Prop(state_type, full_name, **kwargs)
        self.__cached_states[full_name] = cached
        return cached

    def group_for(self, group_name, metadata=None, parent=None):
        group_item = '%s_Group_%s' % (parent.item_base if parent else 'MMDEV', group_name)
        if group_item in self.__cached_groups:
            return self.__cached_groups[group_item]
        group = Prop(
            set, group_item,
            metadata=metadata,
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

            def __getattr__(self, attrib):
                for p, v in self.__device.properties.items():
                    if attrib in {p, translate_camel(p)}:
                        return v
                raise AttributeError()

        return EphemeralDevice(
            room_name=room_name, 
            device_class=Ephemeral, 
            device_name=device_name
        )
