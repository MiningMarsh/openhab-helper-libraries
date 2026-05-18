from functools import wraps
import time
import json


import scope
from openhab import Registry, logger


from . import utils
from . import rules


_PROPS = []
_BOOT = time.time()


@rules.register
@rules.loop
def ensure_items():
    items = set()
    for prop in _PROPS:
        prop._ensure_item()
        items.add(prop.item)

    now = time.time()
    if now - _BOOT < 5 * 60:
        return

    for item in Registry.getItems():
        name = item.getName()
        if not name.startswith('MMDEV_') or name in items:
            continue

        metadata = item.getMetadata().get('mmdev')
        if metadata is None:
            continue
        try:
            heartbeat = float(metadata.getValue())
        except:
            heartbeat = 0

        if now - heartbeat > 5 * 60:
            Registry.removeItem(name)


def ptype(value):
    return scope.PercentType(scope.DecimalType(value).intValue())


class Prop:

    def __init__(self, 
                 item_type, item_name,
                 channel=None,
                 default=None,
                 dimension=None,
                 force=False,
                 groups=None,
                 metadata=None,
                 normalize=False,
                 property_name = None,
                 proxy=None,
                 unit=None,
                 tracing=None):

        if groups is None:
            groups = set()
        if metadata is None:
            metadata = dict()

        if proxy is not None and proxy.__proxy is not None:
            proxy = proxy.__proxy

        self.__tracing = tracing
        self.__default = default
        self.__dimension = dimension
        self.__force = force
        self.__groups = {g.item for g in groups}
        self.__item = item_name
        self.__item_type = item_type
        self.__links = dict()
        self.__normalize = normalize
        self.__property_name = property_name
        self.__proxy = proxy
        self.__unit = unit
        self.__channel = channel
        self.__metadata = {k: v for k, v in metadata.items()}
        if item_type == int:
            oh_type = 'Number'
        elif item_type == float:
            oh_type = 'Dimmer'
        elif item_type == bool:
            oh_type = 'Switch'
        elif item_type == tuple:
            oh_type = 'Color'
        elif item_type == set:
            oh_type = 'Group'
        elif item_type == str:
            oh_type = 'String'
        else:
            parts = item_type.split(':')
            oh_type = parts[0]
            if len(parts) > 1:
                self.__dimension = parts[1]

        if normalize:
            if item_type == int:
                oh_type = 'Dimmer'
            elif item_type == float:
                oh_type = 'Number'

        self.__oh_type = oh_type

        if proxy is None:
            self._ensure_item()
            _PROPS.append(self)
        else:
            for group in self.__groups:
                proxy.__groups.add(group)
            for section, entry in self.__metadata.items():
                section_value, config = entry
                
                if section not in proxy.__metadata:
                    proxy.__metadata[section] = (section_value, {})

                elif proxy.__metadata[section][0] != section_value:
                    proxy.__metadata[section] = (section_value, config)

                for config_key, config_value in config.items():
                    proxy.__metadata[section][1][config_key] = config_value

    @property
    def property_name(self):
        return self.__property_name

    @property
    def __full_type(self):
        if self.__dimension is None:
            return self.__oh_type
        return '%s:%s' % (self.__oh_type, self.__dimension)

    def _ensure_item(self):
        item = utils.suppress(lambda: Registry.getItem(self.__item))
        if item is not None and str(item.getType()) != self.__full_type:
            Registry.removeItem(self.__item)
            item = None
        if item is None:
            config = {
                'label': self.__item,
            }
            if len(self.__groups) != 0:
                config['groups'] = list(sorted(self.__groups))
            item = Registry.addItem(self.__item, self.__full_type, item_config = config)
            if self.__default is not None:
                self.command = self.__default

        if item.getLabel() != self.__item:
            item.setLabel(self.__item)

        for group in item.getGroupNames():
            if group not in self.__groups:
                item.removeGroupName(group)

        for group in self.__groups:
            if group not in item.getGroupNames():
                item.addGroupName(group)

        for link in item.getChannelLinks():
            channel = link.getLinkedUID().getAsString()
            if channel != self.__channel:
                item.unlinkChannel(channel)

        if self.__channel is not None:
            item.linkChannel(self.__channel)

        metadata = item.getMetadata()
        metadata.removeAll()
        target = self.__metadata
        target = json.loads(json.dumps(self.__metadata))
        target['mmdev'] = (str(int(time.time())), {})
        for namespace, values in target.items():
            value, config = values
            metadata.set(namespace, value, config)

    @property
    def value(self):
        if self.__proxy is not None:
            return self.__proxy.value
        v = utils.suppress(lambda: Registry.getItemState(self.__item))
        if v is None or isinstance(v, scope.UnDefType):
            if self.__default is not None:
                return self.__default
            else:
                return None
        if self.__normalize and self.__item_type == int:
            return max(0.0, min(100.0, utils.sanitize(v) * 100.0))
        if self.__normalize and self.__item_type == float:
            return max(0.0, min(1.0, utils.sanitize(v) / 100.0))
        return utils.sanitize(v)
        
    @property
    def command(self):
        if self.__proxy is not None:
            return self.__proxy.command

        def commander(value, force=self.__force):
            item = Registry.getItem(self.__item)
            def action(value):
                try:
                    if force:
                        item.sendCommand(self.__ovalue(value))
                    else:
                        item.sendCommandIfDifferent(self.__ovalue(value))
                except Exception as e:
                    logger.warn(f'Failed command: {type(self.__ovalue(value))}:{self.ovalue(value)} -> {self.__item}')

            if self.__unit is not None:
                action(value)
            elif self.__normalize and self.__item_type == int:
                action(max(0.0, min(1.0, value / 100.0)))
            elif self.__normalize and self.__item_type == float:
                action(max(0.0, min(100.0, value * 100.0)))
            else:
                action(value)
        return commander

    @command.setter
    def command(self, value):
        return self.command(value)
        
    @property
    def update(self):
        if self.__proxy is not None:
            return self.__proxy.update

        def updater(value, force=self.__force):
            item = Registry.getItem(self.__item)
            def action(value):
                try:
                    if force:
                        item.postUpdate(self.__ovalue(value))
                    else:
                        item.postUpdateIfDifferent(self.__ovalue(value))
                except Exception as e:
                    logger.warn(f'Failed update: {type(self.__ovalue(value))}:{self.__ovalue(value)} -> {self.__item}')

            if self.__unit is not None:
                action(value)
            elif self.__normalize and self.__item_type == int:
                action(max(0.0, min(1.0, value / 100.0)))
            elif self.__normalize and self.__item_type == float:
                action(max(0.0, min(100.0, value * 100.0)))
            else:
                action(value)
        return updater

    @update.setter
    def update(self, value):
        return self.update(value)

    def on_change(self, function):
        if self.__proxy is not None:
            return self.__proxy.on_change(function)

        if isinstance(function, rules.Rule):
            r = function
        else:
            r = rules.Rule(function)

        @wraps(function)
        def wrapper(event):
            if not r.pass_context:
                return function()

            old = utils.suppress(lambda: utils.sanitize(event['oldState']))
            new = utils.suppress(lambda: utils.sanitize(event['newState']))

            if self.__normalize:
                if old is not None and self.__item_type == int:
                    old = max(0.0, min(100.0, old * 100))
                elif old is not None and self.__item_type == float:
                    old = max(0.0, min(1.0, old / 100.0))
                if new is not None and self.__item_type == int:
                    new = max(0.0, min(100.0, new * 100))
                elif new is not None and self.__item_type == float:
                    new = max(0.0, min(1.0, new / 100.0))
            if r.null_context or (old is not None and new is not None):
                return function(old, new)

        r.on_change(self.item, wrapper)
        return r

    def on_deactivate(self, function):
        if self.__proxy is not None:
            return self.__proxy.on_deactivate(function)

        if isinstance(function, rules.Rule):
            r = function
        else:
            r = rules.Rule(function)

        @wraps(function)
        def wrapper(event):
            value = utils.suppress(lambda: utils.sanitize(event['command']))
            if value is False:
                return function()
        
        r.on_command(self.item, wrapper)
        return r
        
    def on_activate(self, function):
        if self.__proxy is not None:
            return self.__proxy.on_activate(function)

        if isinstance(function, rules.Rule):
            r = function
        else:
            r = rules.Rule(function)

        @wraps(function)
        def wrapper(event):
            value = utils.suppress(lambda: utils.sanitize(event['command']))
            if value is True:
                return function()

        r.on_command(self.item, wrapper)
        return r


    def on_enable(self, function):
        if self.__proxy is not None:
            return self.__proxy.on_enable(function)

        if isinstance(function, rules.Rule):
            r = function
        else:
            r = rules.Rule(function)

        @wraps(function)
        def wrapper(event):
            new = utils.suppress(lambda: utils.sanitize(event['newState']))
            if new is True:
                return function()
        
        r.on_change(self.item, wrapper)
        return r

    def on_disable(self, function):
        if self.__proxy is not None:
            return self.__proxy.on_disable(function)

        if isinstance(function, rules.Rule):
            r = function
        else:
            r = rules.Rule(function)

        @wraps(function)
        def wrapper(event):
            new = utils.suppress(lambda: utils.sanitize(event['newState']))
            if new is False:
                return function()
        
        r.on_change(self.item, wrapper)
        return r

    def on_command(self, function):
        if self.__proxy is not None:
            return self.__proxy.on_command(function)

        if isinstance(function, rules.Rule):
            r = function
        else:
            r = rules.Rule(function)

        @wraps(function)
        def wrapper(event):
            if not r.pass_context:
                return function()

            command = utils.suppress(lambda: utils.sanitize(event['command']))
            if command is not None and self.__normalize and self.__item_type == int:
                return function(max(0.0, min(100.0, command * 100.0)))
            elif command is not None and self.__normalize and self.__item_type == float:
                return function(max(0.0, min(1.0, command / 100.0)))
            elif r.null_context or command is not None:
                return function(command)
            
        r.on_command(self.item, wrapper)
        return r

    def on_update(self, function):
        if self.__proxy is not None:
            return self.__proxy.on_update(function)

        if isinstance(function, rules.Rule):
            r = function
        else:
            r = rules.Rule(function)
        
        @wraps(function)
        def wrapper(event):
            if not r.pass_context:
                return function()

            update = utils.suppress(lambda: utils.sanitize(event['update']))
            if update is not None and self.__normalize and self.__item_type == int:
                return function(max(0.0, min(100.0, update * 100.0)))
            elif update is not None and self.__normalize and self.__item_type == float:
                return function(max(00.0, min(1.0, update / 100.0)))
            elif null_context or (update is not None):
                return function(update)
        
        r.on_update(self.item, wrapper)
        return r

    @property
    def sync(self):
        if self.__proxy is not None:
            return self.__proxy.sync

        def syncer(prop):
            
            @rules.register
            @rules.pass_context
            @prop.on_command
            def prop_command(value):
                self.command(value)

            @rules.register
            @rules.pass_context
            @self.on_command
            def self_command(value):
                prop.command(value)

        return syncer

    @sync.setter
    def sync(self, prop):
        return self.sync(prop)

    @property
    def follow(self):
        if self.__proxy is not None:
            return self.__proxy.follow

        def follower(prop, force=self.__force):
            try:
                self.command = prop.value
            except:
                pass

            @rules.register
            @rules.pass_context
            @prop.on_command
            def on_command(value):
                self.command(value, force=force)

            @rules.register
            @rules.pass_context
            @prop.on_update
            def on_update(value):
                self.update(value, force=force)

        return follower

    @follow.setter
    def follow(self, prop):
        return self.follow(prop)

    @property
    def invert(self):
        if self.__proxy is not None:
            return self.__proxy.invert

        def inverter(prop, force=self.__force):

            @rules.register
            @rules.pass_context
            @prop.on_command
            def on_command(value):
                if not isinstance(value, bool):
                    self.command(not value, force=force)

            @rules.register
            @rules.pass_context
            @prop.on_update
            def on_update(_, value):
                if isinstance(value, bool):
                    self.update(not value, force=force)

        return inverter

    @invert.setter
    def invert(self, prop):
        return self.invert(prop)

    @property
    def item(self):
        if self.__proxy is not None:
            return self.__proxy.item
        return self.__item

    def __ovalue(self, value):
        if value is None:
            return UnDefType()
        if self.__oh_type == 'Number':
            return value
        elif self.__oh_type == 'Dimmer':
            return max(0.0, min(100.0, 100.0 * value))
        elif self.__oh_type == 'Switch':
            if value:
                return scope.ON
            else:
                return scope.OFF
        elif self.__oh_type == 'String':
            return value
        elif self.__oh_type == 'Color':
            if isinstance(value, tuple) or isinstance(value, list):
                return f'{value[0]},{max(0.0, min(100.0, value[1] * 100.0))},{max(0.0, min(100.0, value[2] * 100.0))}'
            elif isinstance(value, float) or isinstance(value, int):
                return max(0, min(100, 100 * value))
            elif value:
                return scope.ON
            else:
                return scope.OFF
        else:
            print('Unknown type:', type(value))
            return value
