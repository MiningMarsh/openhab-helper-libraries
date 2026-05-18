import time
from mmdev import device, rules


@device.as_device()
def Regulator(device, increasing=True, normalize=False, regulator_type=float, reset_on_activate=False):

    energized = device.property(bool, 'Energized', default=False)
    powered = device.property(bool, 'Powered', default=True)
    mode = device.property(str, 'Mode', default='Automatic')

    setpoint = device.property(
        regulator_type, 
        'Setpoint', 
        default=(
            increasing 
            if regulator_type == bool 
            else 0
        ),
        normalize=normalize
    )

    monitor = device.property(
        regulator_type, 'Monitor', default=0, normalize=normalize
    )
    
    cooldown_period = device.property(
        int, 'CooldownPeriod', default=300
    )

    duty_period = device.property(
        int, 'DutyPeriod', default=300
    )

    window = device.property(
        regulator_type, 'Window', default=300, normalize=normalize
    )

    last_transition = device.property(
        int, 'LastTransition', default=time.time()
    )

    desired = device.property(bool, 'Desired',  default=False)

    @rules.register
    @powered.on_command
    def powered_command():
        mode.command = 'Manual'

    @rules.register
    @rules.loop
    @desired.on_change
    @mode.on_change
    @powered.on_change
    @last_transition.on_change
    @cooldown_period.on_change
    @duty_period.on_change
    def update():
        target = (
            (mode.value.lower() == 'automatic' and desired.value) or
            (mode.value.lower() != 'automatic' and powered.value)
        )

        if energized.command == target:
            return

        now = time.time()
        if not energized.value and target and (now - last_transition.value >= cooldown_period.value):
            energized.command = True
            last_transition.command = now
        elif energized.value and not target and now - last_transition.value >= duty_period.value:
            energized.command = False
            last_transition.command = now

        if mode.value.lower() == 'automatic':
            powered.update = energized.value
    
    @rules.register
    @monitor.on_change
    @setpoint.on_change
    @window.on_change
    def hysterisis():
        value = monitor.value
        if regulator_type is bool:
            if increasing and setpoint.value and not value:
                desired.command = True
            elif increasing and (not setpoint.value or value):
                desired.command = False
            elif not increasing and not setpoint.value and value:
                desired.command = True
            elif not increasing and (setpoint.value or not value):
                desired.command = False
        elif increasing:
            if value < setpoint.value:
                desired.command = True
            elif value >= setpoint.value + window.value:
                desired.command = False
        else:
            if value > setpoint.value:
                desired.command = True
            elif value <= setpoint.value - window.value:
                desired.command = False
        update()

    @rules.register
    @energized.on_change
    def reset_last_transition():
        last_transition.command = time.time()

    if reset_on_activate:
        @rules.register
        @desired.on_activate
        def desired_reset_last_transition():
            if energized.value:
                last_transition.command = time.time()

    update()

    return {
        window,
        setpoint,
        energized,
        duty_period,
        cooldown_period,
        powered,
        mode,
        monitor
    }
