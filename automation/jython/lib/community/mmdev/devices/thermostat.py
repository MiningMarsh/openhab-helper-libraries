from functools import wraps

from .. import device

_MODES={
    'Disabled': 0, 
    'Heat': 1, 
    'Cool': 2, 
    'HeatCool': 3,
    'AwayHeat': 11,
    'AwayCool': 12
}


_FAN_MODES={
    'Auto': 0,
    'On': 1,
    'Circulate': 6
}

def mode_translate(mode_num, mode_defs):
    for mode, num in mode_defs.items():
        if num == mode_num:
            return mode


@device.as_device()
def Thermostat(device):

    overheat = device.property(bool, 'Overheat', default=False)
    overcool = device.property(bool, 'Overcool', default=False)

    group = device.group_for(
        'Thermostat_' + device.room_name.replace(' ', '') + '_' + device.device_name.replace(' ', ''),
        metadata={'ga': ('AC_Unit', {
            'name': device.device_name,
            'roomHint': device.room_name,
            'lang': 'en',
            'useFahrenheit': True,
            'thermostatModes': 'off=Disabled,heat=Heat,cool=Cool,heatcool=HeatCool,auto=Automatic',
            'ordered': True,
            'fanModeName': 'Humidity Regulator,Humidity Regulator',
            'fanModeSettings': 'Automatic=Automatic,Manual=Manual,Disabled=Disabled'
        })}
    )

    temperature = device.property(
        int, 'Temperature', default=0,
        groups={group},
        dimension='Temperature',
        metadata={'ga': ('thermostatTemperatureAmbient', {})}
    )

    controls_humidity_mode = device.property(
        str, 'ControlsHumidityMode', default='Automatic',
        groups={group},
        metadata={'ga': ('fanMode', {})}
    )
    controls_humidity_setpoint = device.property(
        float, 'ControlsHumiditySetpoint', default=0.5,
        groups={group},
        metadata={'ga': ('fanSpeed', {})}
    )

    humidity_setpoint_low = device.property(
        float, 'HumiditySetpointLow', default=0.45
    )

    humidity_setpoint_high = device.property(
        float, 'HumiditySetpointHigh', default=0.55
    )

    humidity = device.property(
        float, 'Humidity', default=0
    )

    filter_life = device.property(
        float, 'FilterLife', default=1
    )

    filter_life_ga = device.property(
        int, 'FilterLifeGA', default=100,
        groups=[group],
        metadata={'ga': ('fanFilterLifeTime', {})}
    )

    @filter_life.on_change(pass_context=True)
    def filter_life_change(_, value):
        filter_life_ga.command = value * 100
    filter_life_ga.command = filter_life.value * 100

    sleeping = device.property(bool, 'Sleeping', default=False)
    away = device.property(bool, 'Away', default=False)
    dog_mode = device.property(bool, 'DogMode', default=False)

    @controls_humidity_setpoint.on_command(pass_context=True)
    def humidity_setpoint_command(value):
        if value == 0:
            controls_humidity_mode.command = 'Disabled'
        else:
            controls_humidity_mode.command = 'Manual'

    @controls_humidity_setpoint.on_change()
    @controls_humidity_mode.on_change()
    @away.on_change()
    @sleeping.on_change()
    @humidity.on_change()
    def update_humidity_setpoints():
        setpoint_low, setpoint_high = 0, 0
        if controls_humidity_mode.value == 'Automatic':
            if away.value:
                setpoint_low, setpoint_high = 0.3, 0.7
            elif sleeping.value:
                setpoint_low, setpoint_high = 0.35, 0.65
            else:
                setpoint_low, setpoint_high = 0.4, 0.6

            if humidity.value < setpoint_low:
                controls_humidity_setpoint.update = setpoint_low
            elif humidity.value > setpoint_high:
                controls_humidity_setpoint.update = setpoint_high
            else:
                controls_humidity_setpoint.update = humidity.value

        elif controls_humidity_mode.value == 'Disabled':
            setpoint_high = 1
            setpoint_loW = 0
            controls_humidity_setpoint.update = 0

        else:
            setpoint_low, setpoint_high = (
                controls_humidity_setpoint.value - 0.05, 
                controls_humidity_setpoint.value + 0.05
            )

        humidity_setpoint_low.command = max(0.0, min(1.0, setpoint_low))
        humidity_setpoint_high.command = max(0.0, min(1.0, setpoint_high))

    pm25 = device.property(
        int, 'PM25', default=0,
        groups=[group],
        metadata={'ga': ('fanPM25', {})}
    )

    humidity_ga = device.property(
        int, 'HumidityGA', default=0,
        groups=[group],
        metadata={'ga': ('thermostatHumidityAmbient', {})}
    )

    @humidity.on_change(pass_context=True)
    def humidity_change(_, value):
        humidity_ga.command = value * 100.0

    controls_mode = device.property(
        str, 'ControlsMode', default='Automatic',
        groups=[group],
        metadata={'ga': ('thermostatMode', {})}
    )

    fan_mode = device.property(int, 'FanMode', default=0)

    controls_setpoint_low = device.property(
        int, 'ControlsSetpointLow', default=68.0,
        groups=[group],
        dimension='Temperature',
        metadata={'ga': ('thermostatTemperatureSetpointLow', {})}
    )

    controls_setpoint_high = device.property(
        int, 'ControlsSetpointHigh', default=72.0,
        groups=[group],
        dimension='Temperature',
        metadata={'ga': ('thermostatTemperatureSetpointHigh', {})}
    )

    setpoint_low = device.property(
        int, 'SetpointLow', default=68.0,
        dimension='Temperature',
    )

    setpoint_high = device.property(
        int, 'SetpointHigh', default=72.0,
        dimension='Temperature'
    )

    mode = device.property(
        int, 'Mode', default=3,
    )

    operation_mode = device.property(str, 'OperationMode', default='Automatic')
    operation_setpoint_high = device.property(int, 'OperationSetpointHigh', default=72)
    operation_setpoint_low = device.property(int, 'OperationSetpointLow', default=68)

    @operation_setpoint_low.on_change()
    @operation_setpoint_high.on_change()
    @operation_mode.on_change()
    @temperature.on_change()
    @device.rule_engine.loop
    def update():
        setpoint_low.command = operation_setpoint_low.value
        if operation_setpoint_low.value >= operation_setpoint_high.value:
            setpoint_high.command = operation_setpoint_low.value
        else:
            setpoint_high.command = operation_setpoint_high.value

        if operation_mode.value == 'HeatCool':
            if temperature.value >= operation_setpoint_high.value + 1.5:
                mode.command = _MODES['Cool']
            elif temperature.value <= operation_setpoint_low.value - 1.5:
                mode.command = _MODES['Heat']
            else: 
                mode.command = _MODES['HeatCool']
        else:
            mode.command = _MODES[operation_mode.value]

    @operation_mode.on_change()
    @operation_setpoint_high.on_change()
    @temperature.on_change()
    def update_overheat():
        overheat.command = bool(
            'Cool' in operation_mode.value
            and temperature.value > operation_setpoint_high.value + 1.0
        )

    @operation_mode.on_change()
    @operation_setpoint_low.on_change()
    @temperature.on_change()
    def update_overcool():
        overcool.command = bool(
            'Heat' in operation_mode.value
            and temperature.value < operation_setpoint_low.value - 1.0
        )

    if controls_mode.value == 'Automatic':
        controls_setpoint_low.update = operation_setpoint_low.value
        controls_setpoint_high.update = operation_setpoint_high.value

    @away.on_change()
    @controls_mode.on_change()
    @dog_mode.on_change()
    @mode.on_change()
    @sleeping.on_change()
    def operation_update():
        if controls_mode.value == 'Automatic':
            if away.value:
                operation_mode.command = (
                    'AwayHeat' 
                    if temperature.value < 70 
                    else 'AwayCool'
                )
                operation_setpoint_low.command = 60
                operation_setpoint_high.command = 80

            elif dog_mode.value:
                operation_mode.command = (
                    'AwayHeat' 
                    if temperature.value < 70 
                    else 'AwayCool'
                )
                operation_setpoint_low.command = 65
                operation_setpoint_high.command = 75

            elif sleeping.value:
                operation_mode.command = 'HeatCool'
                operation_setpoint_low.command = 65
                operation_setpoint_high.command = 65
            
            else:
                operation_mode.command = 'HeatCool'
                operation_setpoint_low.command = 68
                operation_setpoint_high.command = 72
        else:
            operation_mode.command = controls_mode.value
            operation_setpoint_low.command = controls_setpoint_low.value
            operation_setpoint_high.command = controls_setpoint_high.value

    controls_mode.command = 'Automatic'
    operation_update()
    update()

    return {
        controls_mode,
        controls_setpoint_low,
        controls_setpoint_high,
        controls_humidity_mode,
        controls_humidity_setpoint,
        setpoint_low,
        setpoint_high,
        mode,
        fan_mode,
        sleeping,
        away,
        overheat,
        overcool,
        operation_mode,
        operation_setpoint_low,
        operation_setpoint_high,
        humidity,
        temperature,
        controls_humidity_setpoint,
        humidity_setpoint_low,
        humidity_setpoint_high,
        filter_life
    }
