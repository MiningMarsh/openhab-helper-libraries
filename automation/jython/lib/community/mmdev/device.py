from . import log
from core.log import log_traceback
from . import prop
from . import manager
from core.exceptions import suppress
from core.loader import load
from contextlib import contextmanager
from inspect import getmodule
from core.exceptions import suppress
import community.mmdev.devices
import re
from uuid import uuid4


_RE_CAMEL = re.compile('^(.*[a-z])([A-Z].*)$')


def item_base(collection_name, class_name, room_name, device_name, parent=None):
    if parent is None:
        return 'MMDEV_%s_%s_%s_%s' % (
            collection_name, class_name,
            room_name.replace(' ', '') if room_name is not None else '',
            device_name.replace(' ', '')
        )

    return '%s_%s_%s_%s' % (
        parent.item_base, collection_name, class_name,
        device_name.replace(' ', '')
    )


def details(function):
    
    parent = getmodule(function)
    grandparent = suppress(lambda: load('.'.join(parent.__name__.split('.')[:-1])))

    collection = (
        suppress(lambda: function.collection)
        or suppress(lambda: function.device_collection)
        or suppress(lambda: parent.collection)
        or suppress(lambda: parent.device_collection)
        or suppress(lambda: grandparent.collection)
        or suppress(lambda: grandparent.device_collection)
        or suppress(lambda: grandparent.__name__.split('.')[-1])
        or suppress(lambda: parent.__name__.split('.')[-1])
        or 'Undefined'
    )

    name = (
        suppress(lambda: function.name) 
        or suppress(lambda: function.device_name) 
        or suppress(lambda: function.__class__.name)
        or suppress(lambda: function.__class__.device_name)
        or suppress(lambda: function.__name__)
        or suppress(lambda: function.__class__.__name__)
    )

    return collection, name


def translate_camel(name):
    match = _RE_CAMEL.match(name)
    while match is not None:
        begin, end = match.groups()
        name = '%s_%s' % (begin, end)
        match = _RE_CAMEL.match(name)
    return name.lower()


class Device(object):
    def __init__(self, room_name, device_class, device_name, rule_engine, item_base=None, logger=log.LOGGER):
        device_collection, class_name = details(device_class)
        self.class_name = class_name
        self.logger = logger
        self.room_name = room_name
        self.device_collection = device_collection
        self.device_name = device_name
        self.rule_engine = rule_engine
        self.__items = set()
        self.__item_base = item_base
        self.__properties = {}

    @property
    def items(self):
        return self.__items

    @property
    def properties(self):
        return self.__properties

    @property
    def item_base(self):
        if self.__item_base is not None:
            return self.__item_base

        return item_base(
            collection_name, class_name, room_name, device_name
        )

    def property_item(self, property_name):
        return '%s_%s' % (
            self.item_base,
            property_name
        )

    def property(self, property_type, property_name, channel=None, default=None, force=False, normalize=False, metadata=None, groups=None, dimension=None):
        item = self.property_item(property_name)
        self.__items.add(item)
        p = prop.Prop(
            property_type, item,
            default=default,
            logger=self.logger,
            force=force,
            channel=channel,
            normalize=normalize,
            metadata=metadata,
            groups=groups,
            dimension=dimension,
            rule_engine=self.rule_engine,
            property_name=property_name
        )
        self.__properties[property_name] = p
        return p

    def group_for(self, group_name, metadata=None, logger=None):
        group_item = 'MMDEV_Group_' + group_name
        self.__items.add(group_item)
        if logger is None:
            logger = self.logger
        return prop.Prop(
            set, group_item,
            metadata=metadata,
            rule_engine=self.rule_engine,
            property_name=group_name,
            logger=logger
        )


# For some reason, if I dont wrap this inbthis eztra class, the d3vice object is gettibg reused.
class DeviceAttribWrapper(object):

    def __init__(self, device, attribs):
        self.__device = device
        self.__attribs = {}
        for attrib, value in attribs.items():
            self.__attribs[attrib] = value

        self.__attribs['device'] = device

    def __getattr__(self, name):
        if self.__attribs is not None:
            if name in self.__attribs:
                return self.__attribs[name]
        raise AttributeError

def as_device(collection=None, name=None, ephemeral=False, manager=False):
    if ephemeral:
        collection = 'Ephemeral'

    def decorator(function):
        device_collection, device_name = details(function)
        if collection is not None:
            device_collection = collection
        if name is not None:
            device_name = name

        class DeviceManagerWrapper(object):
            
            def __init__(self, device, manager):
                self.__manager = manager
                self.__parent = device

            def device_for(self, device_class, device_name=None, **kwargs):
                if 'parent' not in kwargs:
                    kwargs['parent'] = self.__parent
                if 'room_name' not in kwargs:
                    kwargs['room_name'] = self.__parent.room_name
                return self.__manager.device_for(
                    device_class, device_ne=device_name, **kwargs
                )

            def state_for(self, *args, **kwargs):
                kwargs['parent'] = self.__parent
                return self.__manager.state_for(*args, **kwargs)

            def group_for(self, *args, **kwargs):
                kwargs['parent'] = self.__parent
                return self.__manager.group_for(*args, **kwargs)

            def ephemeral_for(self, *args, **kwargs):
                raise Exception('Cannot spawn nested ephemeral device!')

            @property
            def rule_engine(self):
                return self.__manager.rule_engine

            @property
            def logger(self):
                return self.__manager.logger

        class DeviceClassWrapper(object):
            collection=device_collection
            name=device_name

            def __init__(self, function):
                self.__function = function

            def __params(self, postfix, kwargs):
                m = {}
                postfix = '_{}'.format(postfix)
                for name, value in kwargs.items():
                    if name.endswith(postfix):
                        target = postfix.join(name.split(postfix)[:-1])
                        m[target] = value
                for name in m.keys():
                    del kwargs['{}{}'.format(name, postfix)]
                return m

            def __call__(self, device, **kwargs):
                overrides = {'default', 'metadata', 'channel', 'proxy', 'groups', 'normalize'}
                params = {}
                for name in overrides:
                    params[name] = self.__params(name, kwargs)


                attribs = {}
                exposed = set()
                wrapper = DevicePropertyWrapper(device, params)
                if manager is True:
                    kwargs['manager'] = DeviceManagerWrapper(device, kwargs['manager'])
                for attrib in self.__function(wrapper, **kwargs):
                    if not isinstance(attrib, prop.Prop):
                        attribs[translate_camel(attrib.device.device_name)] = attrib
                    else:
                        name = translate_camel(attrib.property_name)
                        attribs[name] = attrib
                        exposed.add(name)
                for section, names in params.items():
                    for name in names:
                        if name not in exposed:
                            raise Exception('Tried to overload private or non-existant property `%s` on device `%s` with attribute `%s_%s`!' % (name, device_name, name, section))

                return DeviceAttribWrapper(device, attribs)


        class DevicePropertyWrapper(object):
                
                @log_traceback
                def __init__(self, device, params):
                    self.__device = device
                    self.__params = params
                    self.__declared = set()

                @log_traceback
                def property(self, property_type, property_name, **kwargs):
                    if property_name in self.__declared:
                        raise Exception('Property `{}` declared twice!'.format(property_name))
                    self.__declared.add(property_name)

                    item_name = self.__device.property_item(property_name)
                    camel_name = translate_camel(property_name)
                    for section, config in self.__params.items():
                        if camel_name in config:
                            if section == 'groups':
                                if section not in kwargs:
                                    kwargs[section] = config[camel_name]
                                else:
                                    new = set()
                                    for item in config[camel_name]:
                                        new.add(item)
                                    for item in groups:
                                        new.add(item)
                                    kwargs[section] = new
                            else:
                                kwargs[section] = config[camel_name]
                            del config[camel_name]
                    
                    return prop.Prop(
                        property_type, item_name,
                        property_name=property_name,
                        rule_engine=self.__device.rule_engine, 
                        **kwargs
                    )

                def __getattr__(self, attr):
                    if hasattr(self.__device, attr):
                        return getattr(self.__device, attr)

                    raise AttributeError()

        return DeviceClassWrapper(function)
    return decorator
