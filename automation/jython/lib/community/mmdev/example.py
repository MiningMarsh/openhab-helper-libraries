from core.log import log_traceback, getLogger

from community.mmdev.manager import Manager
from community.mmdev.devices.thermostat import Thermostat
from community.mmdev.devices.light import Light
from community.mmdev.devices.purifier import Purifier
from community.mmdev.devices.regulator import Regulator
from community.mmdev.devices.timedlatch import TimedLatch
from community.mmdev.devices.notifier import Notifier
from community.mmdev.devices.inverter import Inverter
import time 
import sys

logger = getLogger('example.py')

m = Manager()

tvoc = m.state_for(
    int, 'TVOC', default=0,
    metadata={'ga': ('Sensor', {
        'name': 'Total VOC',
        'roomHint': 'Bedroom',
        'sensorName': 'VolatileOrganicCompounds',
        'valueUnit': 'PARTS_PER_MILLION'
    })},
    channel='mqtt:topic:sensor_station:tvoc'
)

primary_home = m.state_for(
    bool, 'PrimaryHome', default=True,
    channel='mqtt:topic:tile:primary_home'
)

spouse_home = m.state_for(
    bool, 'SpouseHome', default=True,
    channel='mqtt:topic:tile:spouse_home'
)

dog_home = m.state_for(
    bool, 'DogHome', default=True,
    channel='mqtt:topic:tile:dog_home'
)

def scene(name, default):
    return m.state_for(
        bool, name.replace(' ', ''), default=default,
        metadata={'ga': ('Scene', {
            'name': name, 
            'roomHint': 'OpenHAB'
        })}
    )

sleeping = scene('Sleep Mode', False)
awake = scene('Awake Mode', False)

@sleeping.on_activate
def sleeping_activated():
    awake.command = False

@awake.on_activate
def awake_activated():
    sleeping.command = False

away = scene('Away Mode', False)
dog_mode = scene('Dog Mode', False)

@dog_home.on_change()
@primary_home.on_change()
@spouse_home.on_change()
def away_change():
    away.command = not (
        primary_home.value
        or spouse_home.value
        or dog_home.value
    )

    dog_mode = not (
        primary_home.value
        or spouse_home.value
    ) and (
        dog_home.value
    )


automatic_light_management = scene('Automatic Light Management', True)
automatic_air_purification = scene('Automatic Air Purification', True)

automatic_color_temperature = m.state_for(
    int, 'AutomaticColorTemperature', default=6500,
    channel="mqtt:topic:color_temperature:kelvin"
)

automatic_brightness = m.state_for(
    float, 'AutomaticBrightness', default=1.0,
    channel="mqtt:topic:color_temperature:brightness"
)

@log_traceback
def light(room, name, group=False, has_motion=False):
    if has_motion:
        detector = m.device_for(
            device_class=Regulator,
            room_name=room,
            device_name='Motion Detector',
            monitor_channel="hue:0107:primary:motionsensors_" + room.replace(' ', '').lower() + ":presence",
            duty_period_default=300,
            cooldown_period_default=0,
            powered_default=True,
            energized_default=False,
            regulator_type=bool,
            setpoint_default=False,
            increasing=False,
            reset_on_activate=False
        )
        detector.duty_period.command = 300
        detector.setpoint.command = False
        detector.cooldown_period.command = 0
    else:
        detector = None
    dev = m.device_for(
        device_class=Light,
        room_name=room,
        device_name=name,
        sleeping_proxy=sleeping,
        color_channel="hue:" + ('group' if group else '0210') + ":primary:bulbs_" + room.replace(' ', '').lower() + ":color",
        color_temperature_channel="hue:"+ ('group' if group else '0210') + ":primary:bulbs_" + room.replace(' ', '').lower() + ":color_temperature_abs",
        motion_detected_proxy=detector and detector.energized,
        automatic_color_temperature_proxy=automatic_color_temperature,
        automatic_brightness_proxy=automatic_brightness,
        automatic_mode_proxy=automatic_light_management,
        dog_mode_proxy=dog_mode
    )

    @automatic_light_management.on_activate
    def ativate_auto_light():
        dev.automatic_mode.command = True

    @dev.automatic_mode.on_deactivate
    def ativate_auto_light():
        automatic_light_management.command = False

    return dev

light('Living Room', 'Light', True, True)
light('Hallway', 'Light', True, True)
light('Bathroom', 'Lights', True, True)
light('Bedroom', 'Light', False, False)
light('Bedside', 'Lamp', False, False)
light('Closet', 'Light', True, False)


def purifier(room_name, device_name):
    return m.device_for(
        device_class=Purifier,
        room_name=room_name,
        device_name=device_name,
        sleeping_proxy=sleeping,
        dog_mode_proxy=dog_mode,
        automatic_mode_proxy=automatic_air_purification,
        tvoc_proxy=tvoc,
        pm25_channel='mqtt:topic:' + room_name.replace(' ', '').lower() + '_air_purifier:pm25',
        filter_life_channel='mqtt:topic:' + room_name.replace(' ', '').lower() + '_air_purifier:filter_life',
        fan_speed_channel='mqtt:topic:' + room_name.replace(' ', '').lower() + '_air_purifier:fan_speed'
    )

thermostat_purifier = purifier('Living Room', 'Air Purifier')
bedroom_purifier = purifier('Bedroom', 'Air Purifier')

dumbpurifier = m.ephemeral_for('Bedroom', 'DumbPurifier')
dumbpurifier.property(
    bool, 'Power', default=False,
    channel='tplinksmarthome:hs103:outlet_dumbpurifier:switch'
)

@bedroom_purifier.automatic_mode.on_change()
@bedroom_purifier.automatic_fan_speed.on_change()
def update_dumbpurifier():
    dumbpurifier.power.command = bool(
        bedroom_purifier.automatic_mode.value 
        and bedroom_purifier.automatic_fan_speed > 0.5
    )

thermostat = m.device_for(
    device_class=Thermostat,
    device_name='Thermostat',
    sleeping_proxy=sleeping,
    temperature_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:sensor_temperature',
    humidity_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:sensor_relhumidity',
    humidity_normalize=True,
    fan_mode_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_fanmode',
    setpoint_low_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_setpoint_heating',
    setpoint_high_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_setpoint_cooling',
    mode_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_mode',
    away_proxy=away,
    room_name='Living Room',
    dog_mode_proxy=dog_mode,
    pm25_proxy=thermostat_purifier.pm25,
    filter_life_proxy=thermostat_purifier.filter_life,
    overheat_channel='mqtt:topic:overheat:overheat',
    overcool_channel='mqtt:topic:overcool:overcool'
)

dehumidifier = m.device_for(
    device_class=Regulator,
    room_name='Living Room',
    device_name='Dehumidifier',
    increasing=False,
    regulator_type=float,
    window_default=0.05,
    cooldown_period_default=300,
    duty_period_default=300,
    setpoint_proxy=thermostat.humidity_setpoint_high,
    powered_default=True,
    monitor_proxy=thermostat.humidity,
    energized_channel='tplinksmarthome:hs103:outlet_dehumidifier:switch'
)

bedroom_temp = m.state_for(
    int, "BedroomTemperature", default=0,
    channel='mqtt:topic:sensor_station:temperature',
    dimension='Temperature'
)

bedroom_overheat = m.state_for(bool, 'BedroomOverheat', default=False)

@thermostat.operation_mode.on_change()
@thermostat.operation_setpoint_high.on_change()
@bedroom_temp.on_change()
@dehumidifier.energized.on_change()
def bedroom_overheat_update():
    if 'Cool' not in thermostat.operation_mode.value:
        bedroom_overheat.command = False
    else:
        bedroom_overheat.command = (
            (thermostat.operation_setpoint_high.value + 1.0 < bedroom_temp.value)
            or dehumidifier.energized.value
        )

bedroom_overheat_update()

portableac = m.device_for(
    device_class=Regulator,
    room_name='Bedroom',
    device_name='Portable AC',
    monitor_proxy=bedroom_overheat,
    duty_period_default=30 * 60,
    cooldown_period_default=30 * 60,
    regulator_type=bool,
    setpoint_default=False,
    increasing=False,
    powered_default=True,
    energized_channel='tplinksmarthome:hs300:powerstrip_ac:outlet2#switch'
)

m.state_for(
    int, 'PortableACPower', default=0,
    channel='tplinksmarthome:hs300:powerstrip_ac:outlet2#power'
)

@thermostat.operation_mode.on_change()
@thermostat.operation_setpoint_low.on_change()
@thermostat.operation_setpoint_high.on_change()
def update_devices():
    low = thermostat.operation_setpoint_low
    high = thermostat.operation_setpoint_high

    dehumidifier.powered.command = not (
        'Cool' in thermostat.operation_mode.value
        and thermostat.temperature.value > high
    ) or (
        thermostat.humidity.value > 0.70
    )

@dehumidifier.energized.on_change()
@portableac.energized.on_change()
def set_fan_mode():
    thermostat.fan_mode = (
        'Circulate'
        if dehumidifier.energized.value
        or portableac.energized.value
        else 'Auto'
    )

fan = m.state_for(
    bool, 'BedroomFan', default=False, 
    channel='tplinksmarthome:hs300:powerstrip_bedside:outlet6#switch', 
    force=True
)

lock_inverter = m.device_for(
    device_class=Inverter,
    monitor_channel='mqtt:topic:front_door_lock:locked'
)

lock_notifier = m.device_for(
    device_class=Notifier,
    monitor_proxy=lock_inverter.energized,
)

lock_timer = m.device_for(
    device_class=TimedLatch,
    monitor_proxy=lock_notifier.energized,
    timeout_default=5
)
lock_timer.timeout.command=300

lock = m.device_for(
    device_class=Inverter,
    monitor_proxy=lock_timer.energized,
    energized_channel='mqtt:topic:front_door_lock:locked'
)

@portableac.energized.on_change()
@dehumidifier.energized.on_change()
def fan_power():
    fan.command = portableac.energized.value or dehumidifier.energized.value
