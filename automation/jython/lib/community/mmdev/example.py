from community.mmdev.manager import Manager
from community.mmdev.devices.thermostat import Thermostat
from community.mmdev.devices.light import Light
from community.mmdev.devices.purifier import Purifier
from community.mmdev.devices.regulator import Regulator
from community.mmdev.devices.timedlatch import TimedLatch
from community.mmdev.devices.humidityregulator import HumidityRegulator
from community.mmdev.devices.automaticswitch import AutomaticSwitch
from community.mmdev.device import as_device
from community.mmdev.log import LOGGER
from core.log import log_traceback
import community.mmdev.rules as rules

import time 


m = Manager()


tvoc = m.state_for(
    int, 'TVOC', default=0,
    metadata={
        'ga': ('Sensor', {
            'name': 'Total VOC',
            'roomHint': 'Bedroom',
            'sensorName': 'VolatileOrganicCompounds',
            'valueUnit': 'PARTS_PER_MILLION'
        })
    },
    channel='mqtt:topic:sensor_station:tvoc'
)


bedroom_humidity = m.state_for(
    float, 'BedroomHumidity', default=0.5,
    channel='mqtt:topic:sensor_station:humidity'
)


closet_humidity = m.state_for(
    float, 'ClosetHumidity', default=0.5,
    channel='mqtt:topic:closet_sensors:humidity'
)


primary_home = m.state_for(
    bool, 'PrimaryHome', default=True,
    channel='mqtt:topic:tile:primary_home'
)


spouse_home = m.state_for(
    bool, 'SpouseHome', default=True,
    channel='mqtt:topic:tile:spouse_home'
)


def scene(name_on, name_off, default=None, channel_on=None, channel_off=None):
    off = m.state_for(
        bool, 'Scene' + name_off.replace(' ', ''), 
        default=not default,
        channel=channel_off,
        metadata={
            'ga': ('Scene', {
                'name': name_off,
               'roomHint': 'OpenHAB'
            })
        }
    )

    on = m.state_for(
        bool, 'Scene' + name_on.replace(' ', ''), 
        default=default,
        channel=channel_on,
        metadata={
            'ga': ('Scene', {
                'name': name_on, 
                'roomHint': 'OpenHAB'
            })
        }
    )

    @on.on_enable
    def scene_on_enabled():
        off.update = False

    @off.on_enable
    def scene_off_activated():
        on.update = False

    return on

def control(name, default):
    return m.state_for(
        bool, 'Control' + name.replace(' ', ''), default=default,
        metadata={
            'ga': ('Switch', {
                'name': name,
                'roomHint': 'Controls'
            })
        }
    )


sleeping = scene('Sleeping', 'Awake', False)
away = scene('Away', 'Home', False)
dog_home = scene('Dog Home', 'Dog Away', True, channel_on='mqtt:topic:tile:dog_home')


@dog_home.on_change()
@primary_home.on_change()
@spouse_home.on_change()
def away_change():
    away.command = not(
        primary_home.value
        or spouse_home.value
    )


automatic_light_management = control('Automatic Light Management', True)
automatic_air_purification = control('Automatic Air Purification', True)


automatic_color_temperature = m.state_for(
    int, 'AutomaticColorTemperature', default=6500,
    channel="mqtt:topic:color_temperature:kelvin"
)


automatic_brightness = m.state_for(
    float, 'AutomaticBrightness', default=1.0,
    channel="mqtt:topic:color_temperature:brightness"
)


@sleeping.on_change()
def sleeping_change():
    automatic_light_management.command = True
    automatic_air_purification.command = True


lights = {
    ('Living Room', 'Light', True, True),
    ('Hallway', 'Light', True, True),
    ('Bathroom', 'Lights', True, True),
    ('Bedroom', 'Lamp', False, False),
    ('Bedroom', 'Bedside', False, False),
    ('Closet', 'Light', True, False)
}


def light(room, name, group, has_motion):
    if has_motion:
        #detector = m.device_for(
        #    TimedLatch, room, 'Motion Detector', target=True,
        #    energized_channel="hue:0107:primary:motionsensors_" + room.replace(' ', '').lower() + ":presence",
        #    timeout_default=300
        #)
        detector = None
    else:
        detector = None
    dev = m.device_for(
        Light, room, name,
        sleeping_proxy=sleeping,
        automatic_brightness_proxy=automatic_brightness,
        automatic_color_temperature_proxy=automatic_color_temperature,
        automatic_mode_proxy=automatic_light_management,
        away_proxy=away,
        dog_mode_proxy=dog_home,
        motion_detected_proxy=detector and detector.energized,
        color_channel=(
            "hue:" 
            + ('group' if group else '0210') 
            + ":primary:bulbs_" 
            + (
                room.replace(' ', '').lower() 
                if group else 
                room.lower().replace(' ', '') + '_' + name.lower()
            ) 
            + ":color"
        )
    )

    if detector is not None:
        @automatic_light_management.on_enable
        def enable_motion_detector():
            detector.powered.command = True

    remote_channel = "hue:0820:primary:dimmers_%s:dimmer_switch_event" % room.lower().replace(' ', '')

    @rules.on_trigger(remote_channel, pass_context=True)
    def remote_event(channel, event):
        event = int(float(event))
        if 1002 == event:
            dev.controls.command = True
        elif 2002 == event:
            dev.controls.command = max(0, min(1, dev.controls.value[2] + 0.2))
        elif 2003 == event:
            dev.controls.command = 1
        elif 3002 == event:
            dev.controls.command = max(0.05, min(1, dev.controls.value[2] - 0.2))
        elif 3003 == event:
            dev.controls.command = 0.05
        elif 4002 == event:
            dev.controls.command = False


for room, name, group, has_motion in lights:
    light(room, name, group, has_motion)


def purifier(room_name, device_name):
    purifier_group = m.group_for(
        room_name.replace(' ', '') + 'AirPurifier' + device_name.replace(' ', ''),
        metadata={
            'ga': ('AirPurifier', {
                'lang': 'en',
                'name': device_name,
                'roomHint': room_name,
                'fanModeName': 'Control Mode',
                'fanModeSettings': 'Automatic=Automatic,Manual=Manual'
            })
        }
    )

    p = m.device_for(
        Purifier, room_name, device_name,
        controls_groups={purifier_group},
        controls_metadata={'ga': ('fanSpeed', {})},
        dog_mode_proxy=dog_home,
        fan_mode_groups={purifier_group},
        fan_mode_metadata={'ga': ('fanMode', {})},
        fan_speed_channel='mqtt:topic:' + room_name.replace(' ', '').lower() + '_air_purifier:fan_speed',
        filter_life_channel='mqtt:topic:' + room_name.replace(' ', '').lower() + '_air_purifier:filter_life',
        filter_life_groups={purifier_group},
        filter_life_metadata={'ga': ('fanFilterLifeTime', {})},
        pm25_channel='mqtt:topic:' + room_name.replace(' ', '').lower() + '_air_purifier:pm25',
        pm25_groups={purifier_group},
        pm25_metadata={'ga': ('fanPM25', {})},
        sleeping_proxy=sleeping,
        tvoc_proxy=tvoc,
        automatic_mode_proxy=automatic_air_purification
    )

    return p


thermostat_purifier = purifier('Living Room', 'Smart Purifier')
bedroom_purifier = purifier('Bedroom', 'Smart Purifier')


dumbpurifier_group = m.group_for(
    'BedroomPurifier',
    metadata={
        'ga': ('AirPurifier', {
            'lang': 'en',
            'name': 'Air Purifier',
            'roomHint': 'Bedroom',
            'fanModeName': 'Control Mode',
            'fanModeSettings': 'Automatic=Automatic,Manual=Manual',
        })
    }
)


dumbpurifier = m.device_for(
    AutomaticSwitch, 'Bedroom', 'Air Purifier',
    controls_groups={dumbpurifier_group},
    controls_metadata={'ga': ('fanPower', {})},
    mode_groups={dumbpurifier_group},
    mode_metadata={'ga': ('fanMode', {})},
    energized_channel='tplinksmarthome:hs103:outlet_dumbpurifier:switch'
)


@automatic_air_purification.on_enable
def automatic_air_purification_enabled():
    dumbpurifier.mode.command = 'Automatic'


@dumbpurifier.mode.on_change(pass_context=True)
def dumbpurifier_mode_change(_, change):
    if change.lower().strip() != 'automatic':
        automatic_air_purification.command = False


@bedroom_purifier.automatic_mode.on_change()
@bedroom_purifier.automatic_fan_speed.on_change()
def update_dumbpurifier():
    dumbpurifier.monitor.command(
        bedroom_purifier.automatic_fan_speed.value > 0.5
    )


thermostat = m.device_for(
    Thermostat, 'Living Room', 'Thermostat',
    away_proxy=away,
    dog_mode_proxy=dog_home,
    fan_mode_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_fanmode',
    humidity_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:sensor_relhumidity',
    humidity_normalize=True,
    mode_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_mode',
    overcool_channel='mqtt:topic:overcool:overcool',
    overheat_channel='mqtt:topic:overheat:overheat',
    setpoint_high_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_setpoint_cooling',
    setpoint_low_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:thermostat_setpoint_heating',
    sleeping_proxy=sleeping,
    temperature_channel='zwave:honeywell_th6320zw_00_000:controller:thermostat:sensor_temperature'
)


livingroom_humidifier = m.state_for(
    bool, 'LivingRoomHumidifier', default=False,
    channel='tplinksmarthome:hs300:powerstrip_livingroom:outlet5#switch'
)


bedroom_humidifier = m.state_for(
    bool, 'BedroomHumidifier', default=False,
    channel='tplinksmarthome:hs300:powerstrip_ac:outlet5#switch'
)


@closet_humidity.on_change(pass_context=True)
def update_bedroom_humidifier(_, new):
    bedroom_humidifier.command = new < 0.5


@thermostat.humidity.on_change(pass_context=True)
def update_livingroom_humidifier(_, new):
    livingroom_humidifier.command = new < 0.5


humidity_regulator = m.device_for(
    HumidityRegulator, 'Controls', 'Humidity Regulator',
    monitor_proxy=thermostat.humidity
)


dehumidifier = m.device_for(
    Regulator, 'Bedroom', 'Dehumidifier',
    increasing=False,
    regulator_type=float,
    window_default=0.05,
    cooldown_period_default=300,
    duty_period_default=300,
    powered_default=True,
    setpoint_default=0.5,
    monitor_proxy=thermostat.humidity,
    energized_channel='tplinksmarthome:hs103:outlet_dehumidifier:switch'
)


bedroom_temp = m.state_for(
    int, "BedroomTemperature", default=0,
    channel='mqtt:topic:closet_sensors:temperature',
    dimension='Temperature',
    metadata={
        'ga': ('TemperatureSensor', {
            'name': 'Bedroom Temperature',
            'roomHint': 'Bedroom',
            'useFahrenheit': True
        })
    }
)


bedroom_humidity = m.state_for(
    float, 'BedroomHumidity', default=0.5,
    channel='mqtt:topic:closet_sensors:humidity',
    dimension='Humidity',
    metadata={
        'ga': ('HumiditySensor', {
            'name': 'Bedroom Humidity',
            'roomHint': 'Bedroom'
        })
    }
)


bathroom_temp = m.state_for(
    int, "BathroomTemperature", default=0,
    channel='hue:0302:primary:temperaturesensors_bathroom:temperature',
    dimension='Temperature',
    metadata={
        'ga': ('TemperatureSensor', {
            'name': 'Bathroom Temperature',
            'roomHint': 'Bathroom',
            'useFahrenheit': True
        })
    }
)


bathroom_rugheater = m.state_for(
    bool, 'BathroomRugHeater', default=True,
    channel='tplinksmarthome:hs103:outlet_rugheater:switch'
)


@bathroom_temp.on_change(pass_context=True)
def rugheater_update(_, temp):
    bathroom_rugheater.command = temp < 75


hallway_temp = m.state_for(
    int, "HallwayTemperature", default=0,
    channel='hue:0302:primary:temperaturesensors_hallway:temperature',
    dimension='Temperature',
    metadata={
        'ga': ('TemperatureSensor', {
            'name': 'Hallway Temperature',
            'roomHint': 'Bathroom',
            'useFahrenheit': True
        })
    }
)


@as_device(name='PortableAC', ephemeral=True)
def PortableAC(device):
    energized = device.property(bool, 'Energized', default=False)
    last_transition = device.property(int, 'LastTransition', default=0)
    power_usage = device.property(int, 'PowerUsage', default=0)

    @energized.on_change()
    def portableac_last_transition():
        last_transition.command = time.time()

    @thermostat.operation_mode.on_change()
    @thermostat.operation_setpoint_high.on_change()
    @bedroom_temp.on_change()
    @dehumidifier.energized.on_change()
    @last_transition.on_change()
    @device.rule_engine.loop
    def portableac_update():
        if time.time() - last_transition.value < 30 * 60:
            return

        if 'cool' not in thermostat.operation_mode.value.lower():
            energized.command = False
            return

        energized.command = bedroom_temp.value > thermostat.operation_setpoint_high.value

    return {
        energized,
        power_usage
    }


portableac = m.device_for(
    device_class=PortableAC,
    room_name='Bedroom',
    device_name='PortableAC',
    energized_channel='tplinksmarthome:hs300:powerstrip_ac:outlet2#switch',
    power_usage_channel='tplinksmarthome:hs300:powerstrip_ac:outlet2#power'
)


m.device_for(
    TimedLatch, 'Hallway', 'Lock',
    energized_channel='mqtt:topic:front_door_lock:locked',
    monitor_channel='mqtt:topic:front_door_lock:locked',
    powered_default=True,
    latched=False,
    timeout_default=600,
    energized_metadata={
        'ga': ('Lock', {
            'name': 'Front Door Lock',
            'roomHint': 'Hallway'
        })
    }
)


fan = m.state_for(
    bool, 'BedroomFan', default=False,
    channel='tplinksmarthome:hs300:powerstrip_bedside:outlet6#switch'
)


@thermostat.operation_mode.on_change()
@thermostat.operation_setpoint_high.on_change()
@thermostat.temperature.on_change()
@thermostat.humidity.on_change()
@bedroom_humidity.on_change()
def update_dehumidifier():
    dehumidifier.powered.command = (not (
        'Cool' in thermostat.operation_mode.value
        and thermostat.temperature.value >= thermostat.operation_setpoint_high.value + 2.0
    )) and ((
        thermostat.humidity.value > 0.60
    ) or (
        bedroom_humidity.value > 0.60
    ))

update_dehumidifier()


@dehumidifier.energized.on_change()
@portableac.energized.on_change()
@sleeping.on_change()
def update_fan():
    fan.command = (sleeping.value and (
        portableac.energized.value 
        or dehumidifier.energized.value
    )) or (
        portableac.energized.value and ((
            bedroom_temp.value < thermostat.operation_setpoint_high.value
            and thermostat.temperature.value > thermostat.operation_setpoint_high.value
        ) or (
            bedroom_temp.value > thermostat.operation_setpoint_high.value + 5.0
        ))
    )

update_fan()


thermostat.controls_fan_mode.command = 'Auto'
