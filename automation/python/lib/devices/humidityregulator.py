from mmdev import device, rules


@device.as_device()
def HumidityRegulator(device):

    group = device.group_for(
        'HumidityRegulator' + device.device_name.replace(' ', ''),
        metadata={'ga': ('Fan', {
            'fanModeName': 'Control Mode',
            'fanModeSettings': 'Automatic=Automatic,Manual=Manual',
            'roomHint': device.room_name,
            'name': device.device_name
        })}
    )

    monitor = device.property(float, 'Monitor', default=0.5)
    setpoint = device.property(
        float, 'Setpoint', default=0.5,
        metadata={'ga': ('fanSpeed', {})},
        groups={group}
    )
    setpoint_low = device.property(float, 'SetpointLow', default=0.4)
    setpoint_high = device.property(float, 'SetpointHigh', default=0.6)
    control = device.property(float, 'Control', default=0.5)
    mode = device.property(
        str, 'Mode', default='Automatic',
        metadata={'ga': ('fanMode', {})},
        groups={group}
    )

    @rules.register
    @control.on_command
    def control_command():
        mode.command = 'Manual'

    @rules.register
    @rules.pass_context
    @mode.on_change
    def mode_change(_, value):
        if value == 'manual':
            mode.command = 'Manual'
        elif value == 'automatic':
            mode.command = 'Automatic'

    @rules.register
    @control.on_change
    @mode.on_change
    def update():

        value = monitor.value

        if mode == 'Manual':
            setpoint.command = control.value
            setpoint_low.command = setpoint.value - 0.025
            setpoint_high.command = setpoint.value + 0.025
            return

        setpoint_low.command = 0.4
        setpoint_high.command = 0.6

        if value > setpoint_high.value:
            setpoint.command = setpoint_high.value
        elif value < setpoint_low.value:
            setpoint.command = setpoint_low.value
        else:
            setpoint.command = value

    return {
        mode,
        control,
        setpoint,
        setpoint_low,
        setpoint_high,
        monitor
    }
