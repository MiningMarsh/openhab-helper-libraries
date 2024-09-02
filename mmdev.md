# mmdev

`mmdev` is a community library for openhab's jsr223 jython extension. It 
allows you to define your entire item and rule configuration in python, and is designed to have a simple to use interface. It generates and maintains the underlying items and rules automatically based on an object/event model that you define.

`mmdev` resembles an ORM to some extent. The primary goal of this library is to allow you to define behaviors between groups of items without having to use complex rule DSL logic. All logic is instead driven by standard python callback functions.

Here is a small example defining a fan that turns on when the weather temperature exceeds a certain value, but only while a power toggle is switched on. Additionally, the fan switch is exposed over google assistant via user-provided metadata:

```python2
from community.mmdev.device import as_device
from community.mmdev.manager import Manager

# Here we define the class definition for fan devices.
@as_device(ephemeral=True)
def Fan(device):
    
    # Define the properties/items driving this device class.
    energized = device.property(bool, 'Energized', default=False)
    monitor = device.property(bool, 'Monitor', default=False)
    powered = device.property(bool, 'Powered', default=False)
    setpoint = device.property(int, 'Setpoint', default=False, dimension='Temperature')

    # Here we define the behavior of this device, using property events.
    @monitor.on_change()
    @powered.on_change()
    def update():

        # This commands the item backing `energized`.
        energized.command = (

            # This retrieves the current value of the item backing `powered`,`monitor` and `setpoint` and translates them to native python typed values.
            powered.value and monitor.value > setpoint.value
        )

    # This declares the list of properties we want publicly exposed.
    return {
        energized,
        monitor,
        powered,
        setpoint
    }

# Create a device manager we can use to create device objects.
m = Manager()

# Create a free-floating temperature state property.
temperature = m.state_for(
    int, 'Temperature', default=70,
    channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:sensor_temperature'
)

# Create a fan object, overriding the item for its monitor property and attaching the appropriate channel.
fan = m.device_for(
    device_class=Fan,
    device_name='Desk Fan',
    room_name='Study',
    energized_channel='tplinksmarthome:hs300:powerstrip_ac:outlet2#switch',
    monitor_proxy=temperature
)

# At this point, any time the temperature channel changes on the temperature state object, the fan device will toggle the outlet channel as needed.
```

## Installation

To install mmdev, download [this zip](https://github.com/MiningMarsh/openhab-helper-libraries/archive/refs/heads/mmdev.zip) and copy the automation folder to the root of your openhab configuration folder.

`mmdev` comes with an extended, maintained version of Ivan's Helper Libraries. I have attempted to remain as backwards compatible as possible, but I may have missed something. If my version of the helper libraries breaks existing scripts, please let me know.

`mmdev` will not work with other versions of the helper libraries.

## Usage

Put user scripts in `automation/jsr223/lib/python/personal`.

Place extra community libraries in `automation/jython/lib/community`.

## Object Modelling

OpenHAB has native to it the concept of items, indivual values that can be tied
to a channel. `mmdev` treats collections of these items as objects akin to real
world devices. For example, a `fan` device might have a `power` and `speed` item
associated with it that represents the power and speed of a real fan. `mmdev` refers to these objects as devices.

Devices are designed to allow you to declare a group of behaviors for a set of real world devices exactly once. You can then instantiate multiple devices using that declared behavior, generating items for each.

Devices are defined as python classes that describe the items they use and the 
rules they have between them. `mmdev` refers to its equivalent of items as 
device properties.

Devices have a room and a name associated with them. Two devices with the same 
type, name, and room should not be created, as this could lead to erratic 
behavior with the items backing the device properties.

### Devices

Devices are represented by objects in python. Publicly available properties are
exposed as attributes on those objects.

A device property is used the same way both when defining a device class or 
accessing the fields on a device object. They can be used to change or query 
the state of an item or to create rules around that item.

### Collections

Devices have an associated collection name and class name. Collections are 
community modules defining a set of device classes that can be used with 
`mmdev`. `mmdev` has a number of objects it provides out of the box in a 
collection named `Builtin`.

The collection of a device can either be provided with the device definition, or it can be auto-detected.

Auto detection works as follows:

The grandparent of the current module is imported. If it imports successfully, and has a field 'collection' on it, that field is used. Otherwise, the name of the module is used as the collection. If the grandparent cannot be imported, it instead imports the parent and repeats the same process.

A device name is discovered based on the function name given during device definition.

### Properties

Properties wrap a single item each. Once a property is defined, `mmdev` will
begin to maintain the item backing it transparently whenever a new device is instantiated..

#### Property Items

The underling item backing a property is auto-generated based on the `name`, 
`class_name`, `collection_name`, and `room_name` of a device.

You can query the item name of a property's item using the `.item` attribute:

```python2
p = device.property(...)
LOGGER.info(p.item)
```

You can also query a device for the prefix it uses when generating items, or query a device for the item base name it would use for a property:

```python2
LOGGER.info(device.item_base)
LOGGER.info(device.property_item('property_name'))
```

#### Property Values and Types

Properties do not provide or accept raw OpenHAB typed values. Instead, `mmdev` translates openhab typed values to python typed values and vice-versa, transparently.

OpenHAB Types are directly translated to corresponding python types:
    - `DecimalType` values use the `int` type.
    - `OnOffType` values use the `bool` type.
    - `PercentType` values use the `float` type and should be a normalized value.
    - `HSBType` values use the `tuple` type, specifically a tuple of the form `(h, s, b)`.
    - `String` values use the `str` type.
    - `Group` values use the `set` type.
    - `Undefined` openhab values translate to `None`, and vice versa.

Numeric values can have a dimension added with the `dimension` parameter in the property constructor. An example dimension would be 'Temperature'.

A unit can be assigned to a numeric type with the `unit` parameter in the property constructor. When a value is assigned, the corresponding QuanityType is sent instead.

The value of a property can be retrieved by inspecting it's `.value` attribute. No caching is performed; every access will re-query openhab for the value and re-translate it.

### Property Mutation

The value of a property, like an item, can receive both a command and an update. By default, any updates or commands sent to a property are ignored if they are equivalent to the already set value. This can be specified either in the property constructor, or in individual command and update calls:

```
# declare a Num property.
p = device.property(int, 'Num', force=True)

# Num is commanded to 1
p.command = 1

# Num is updated to 2
p.update = 2

# Num is commanded to 2
p.command = 2

# Nothing happens
p.command(2, force=False)
```

### Property Rules

OpenHAB supports a rule engine based on item changes. Likewise, `mmdev` supports rules based on property value changes.

Every property exposes several decorator properties, which when used on a function or method, declares the appropriate underlying OpenHAB rules.

#### `property.on_change()`

Functions decorated with the `on_change` decorator will trigger any time the value of a property changes. If called without arguments, the callback will be called with no arguments. If passed the `pass_context=True` parameter, the callback will be called with the old value and new value passed as arguments. By default, `pass_context` will never pass None values to the callback function; you can override this with the `null_context=True` parameter.

```
p = device.property(int, 'Value', default=0)

@p.on_change(pass_context=True)
def log_changes(_, new):
    LOGGER.log('New Value: {}'.format(new))
```

#### `property.on_command()`

Functions decorated with the `on_command` decorator will trigger any time a property receives a command. If called without arguments, the callback will be called with no arguments. If the `pass_context=True` parameter is passed, the callback will be called with the commanded value passed as an argument. By default, `pass_context` will never pass None values to the callback function; you can override this with the `null_context=True` parameter.

```
p = device.property(int, 'Value', default=0)

@p.on_command(pass_context=True)
def log_command(command):
    LOGGER.log('New Command: {}'.format(command))
```

#### `property.on_update()`

Functions decorated with the `on_update` decorator will trigger any time a property receives an update. If called without arguments, the callback will be called with no arguments. If passed the `pass_context=True` parameter, the callback will be called with the commanded value passed as an argument. By default, `pass_context` will never pass None values to the callback function; you can override this with the `null_context=True` parameter.

```
p = device.property(int, 'Value', default=0)

@p.on_update(pass_context=True)
def log_update(update):
    LOGGER.log('New Update: {}'.format(update))
```

#### `property.on_activate`

Calls a callback whenever the value transitions to the value `True`.

```python2
p = device.property(int, 'Value', default=0)

@p.on_activate
def activated(update):
    LOGGER.log('Activated')
```

#### `property.on_deactivate`

Calls a callback whenever the value transitions to the value `False`.

```python2
p = device.property(int, 'Value', default=0)

@p.on_deactivate
def activated(update):
    LOGGER.log('Deactivated')
```

### The Rule Engine

`mmdev` has an underlying rule engine object it uses to declare its rules. The rule engine associated with a device is available on that device as the `rule_engine` attribute. This usually isn't useful, but there is one decorator that is available from the rule engine that is very useful.

`device.rule_engine.loop` is a special decorator that registers a callback to execute once a minute. It also automatically distributes the timers across the time span of a minute, so that the rule load is a little more evenly distributed.

```
@device.rule_engine.loop
def log():
     LOGGER.info('Loop')
```

If you need a rule that is not available via the aforementioned methods, you can share any rule you like with a `rule` decorator bundled with `mmdev`. Rules decorated with this decorator will have the event object associated with the rule passed to them if they specify `pass_confext=True`.

```python2
from community.mmdev.rules import rule

@rule("cron '...')
def update():
    LOGGER.info('cron')
```

### Property Channels

Each property can have a single optional channel attached to it. This channel is declared when creating the property:

```python2
power = device.property(
    int, 'PortableACPower', default=0,
    channel='tplinksmarthome:hs300:powerstrip_ac:outlet2#power'
)
```

### Property Defaults

The items backing a property can be given a default value. This value is assigned to the property either the first time the item is created, or any time openhab boots while the property contains `None`. The default value is specified as part of the property constructor:

```python2
power = device.property(
    int, 'PortableACPower', default=0,
    channel='tplinksmarthome:hs300:powerstrip_ac:outlet2#power'
)
```

### Property Groups

Properties support having OpenHAB groups assigned to them during property construction via the `groups` parameter.

The value passed to this parameter *MUST BE* a property object, not an item name:

```python2
g1 = device.group_for('TestGroup1')
g2 = device.group_for('TestGroup2')

device.property(
    groups={g1, g2},
    ...
)
```

### Property Proxying

When a property is instantiated, a proxy property can be provided alongside it. If a proxy property is provided, then no new item is created, and all property method calls on the new property will be redirected to call the proxy property's methods. Metadata and groups will be actively merged with the existing metadata and groups on the proxied property.

```python2
test = device.property(int, 'Test', default=False)
proxy = device.property(int, 'Proxy', proxy=test)

# The underlying item for the Proxy property is never created.
```

## Groups

Groups are set type properties with no associated device.

Groups can be created either with either the device object's, or device manager object's, `group_for` method. Both accept a metadata parameter for the group's metadata.

```python2
m = Manager()
g = m.group_for('Test', metadata={})
```

```python2
g = device.group_for('Test', metadata={})
```

## State Properties

State properties are properties unbound from a device, and can be created with a device manager's `state_for` method. It accepts all the same parameters as a device property.

```python2
m = Manager()
sleeping = m.state_for(bool, 'Sleeping', default=False)
```

## Ephemeral Devices

Special ephemeral device objects can be created with the device manager's `ephemeral_for` method. It requires a room and device name, and returns a special device object. This device object has an overridden `property` method on it that, in addition to creating a property, also exposes it as an attribute on the device object. The name of the attribute is determined by converting it from `CamelCase` to `camel_case`, where spaces are stripped before conversion.

```python2
m = Manager()
dev = m.ephemeral_for('Living Room', 'Test')
test = dev.property(bool, 'Test', default=False)

@dev.test.on_change()
def test_change():
    LOGGER.error(test.value)
```

## Defining a Device Class

Device classes are very simple:
The class object can have an optional `collection` and `name` attribute defining the device class collection and device class name. If not defined, the collection and name will be inferred from the module path of the device, and the device class name, respectively.

All device classes must have an __init__ function that accepts a single parameter `device` (in addition to self) and any number of keyword parameters. Keyword parameters can be provided to the device manager when creating an instance of the device.

### Using the `@as_device` helper

Instead of creating a device class directly, it is recommended that you use the `@as_device` decorator from `community.mmdev.device` when defining device classes. This decorator optionally accepts both a specific collection and device name, which are otherwise inferred.

The decorator takes a function with a singular parameter `device` and any number of keyword arguments. The keyword arguments can be provided when instantiating the device with a device manager.

The function is called when the device is created. It is passed a device object that the function can define properties on, and define behaviors around. Finally, the function returns a set of properties it wants exposed publicly, or the empty set of the entire device is private.

The device object also allows the function to create groups specific to the device with the `group_for` method, and allows access to a rule engine if needed through it's `rule_engine` attribute.

Finally, if you pass it the `ephermeral=True` parameter, it will generate a random collection and name to avoid clashing with any other existing device classes. This is useful when used in your startup scripts.

Here is an example defining a Lock class which locks itself if it has been unlocked for longer than a specified time (60 seconds by default):

```
from time import time
from community.mmdev.device import as_device

@as_device(collection='Example')
def Lock(device, timeout=60):

    locked = device.property(bool, 'Locked', default=False)
    last_transition = device.property(int, 'LastTransition', default=0)

    @locked.on_change()
    def transition():
        last_transition.command = time()

    @device.rule_engine.loop
    def check_lock():
        if time() - last_transition.value < timeout:
            return

        if locked.value:
            return

        locked.command = True

    return {
        locked
    }

from community.mmdev.manager import Manager

m = Manager()

lock = m.device_for(
    device_class=Lock,
    room_name='Hallway',
    device_name='Lock',
    timeout=300
)
```

The property set returned from the function does two things:
- It exposes the properties as attributes on the resulting device object. The attribute names are based on the property names after translation from `CamelCase` to `camel_case` while ignoring spaces.
- It exposes a number of keyword arguments to influence the created properties.

The keyword arguments take the following form, where `prop` is the property name of the created property:
- `{prop}_channel`
- `{prop}_groups`
- `{prop}_metadata`
- `{prop}_default`
- `{prop}_proxy`
- `{prop}_normalize`

These keyword arguments will pass themselves to the underlying property's constructor when the function creates it. This is only done for returned properties, all other properties can be seen as "private properties".

```python2
lock = m.device_for(
    room_name='Hallway',
    device_name='Lock',
    locked_channel='mqtt:topic:locked:hallway'
)
```

This is the primary reason using `@as_device` is recommended: The extra keyword arguments gives you an easy way to assign channels and groups to devices as needed.

## Garbage Collection

Item creation and garbage collection works in the following way:

All items created by properties have a heartbeat in their metadata. A cron job updates it once a minute for each live item that `mmdev` knows about.

A garbage collection daemon checks once a minute, and deletes any items that have a heartbeat older than 5 minutes.

When items are created, `mmdev` will delay itself for a couple minutes to allow the item to appear and get initialized. Only after this wait will it create items. This means a fresh boot might take a few minutes before you see object behavior working. This is fine so that persistent items have time to restore their value before you use them.

This method of garbage collection was chosen as it allows items from multiple user scripts to co-exist easily,  and with a lack of any available IPC mechanisms.

All `mmdev` items begin with `MMDEV_`, and the garbage collector will ignore any item that doesn't follow that pattern.

## Example User Script

Since all my security tokens exist in things configuration, I currently keep a copy of the script that controls my apartment at: `automation/jython/lib/community/mmdev/example.py`
