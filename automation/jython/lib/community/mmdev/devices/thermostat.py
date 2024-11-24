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
    'auto': 0,
    'on': 1,
    #'circulate': 6
    'circulate': 0
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
        metadata={'ga': ('Thermostat', {
            'name': device.device_name,
            'roomHint': device.room_name,
            'lang': 'en',
            'useFahrenheit': True,
            'thermostatModes': 'off=Disabled,heat=Heat,cool=Cool,heatcool=HeatCool,auto=Automatic',
            'ordered': True
        })}
    )

    fan_mode = device.property(int, 'FanMode', default=0)
    controls_fan_mode = device.property(str, 'ControlsFanMode', default='auto')

    humidity = device.property(
        float, 'Humidity', default=0.5
    )

    humidity_ga = device.property(
        int, 'HumidityGA', default=50,
        groups={group},
        metadata={'ga': ('thermostatHumidityAmbient', {})}
    )

    @humidity.on_change(pass_context=True)
    def humidity_change(_, new):
        humidity_ga.command = new * 100.0

    temperature = device.property(
        int, 'Temperature', default=0,
        groups={group},
        dimension='Temperature',
        metadata={'ga': ('thermostatTemperatureAmbient', {})}
    )

    sleeping = device.property(bool, 'Sleeping', default=False)
    away = device.property(bool, 'Away', default=False)
    dog_mode = device.property(bool, 'DogMode', default=False)

    controls_mode = device.property(
        str, 'ControlsMode', default='Automatic',
        groups={group},
        metadata={'ga': ('thermostatMode', {})}
    )

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

    operation_mode = device.property(str, 'OperationMode', default='HeatCool')
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


    @away.on_change()
    @controls_mode.on_change()
    @dog_mode.on_change()
    @mode.on_change()
    @sleeping.on_change()
    def operation_update():
        if controls_mode.value.lower() == 'automatic':
            controls_setpoint_low.update = operation_setpoint_low.value
            controls_setpoint_high.update = operation_setpoint_high.value
            if away.value and dog_mode.value:
                operation_mode.command = (
                    'AwayHeat' 
                    if temperature.value < 70 
                    else 'AwayCool'
                )
                operation_setpoint_low.command = 65
                operation_setpoint_high.command = 75

            elif away.value:
                operation_mode.command = (
                    'AwayHeat' 
                    if temperature.value < 70 
                    else 'AwayCool'
                )
                operation_setpoint_low.command = 60
                operation_setpoint_high.command = 80

            elif sleeping.value:
                operation_mode.command = 'HeatCool'
                operation_setpoint_low.command = 60
                operation_setpoint_high.command = 60
            
            else:
                operation_mode.command = 'HeatCool'
                operation_setpoint_low.command = 72
                operation_setpoint_high.command = 72
        else:
            operation_mode.command = controls_mode.value
            operation_setpoint_low.command = controls_setpoint_low.value
            operation_setpoint_high.command = controls_setpoint_high.value

    @controls_fan_mode.on_change(pass_context=True)
    def controls_fan_mode_change(_, value):
        if value.lower() in _FAN_MODES:    
            fan_mode.command = _FAN_MODES[value.lower()]

    operation_mode.command = 'HeatCool'
    operation_update()
    update()

    return {
        away,
        controls_mode,
        controls_setpoint_high,
        controls_setpoint_low,
        mode,
        operation_mode,
        operation_setpoint_high,
        operation_setpoint_low,
        overcool,
        overheat,
        setpoint_high,
        setpoint_low,
        sleeping,
        temperature,
        humidity,
        controls_fan_mode,
        fan_mode
    }
