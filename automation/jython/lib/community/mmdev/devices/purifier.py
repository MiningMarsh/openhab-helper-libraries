from .. import device


@device.as_device()
def Purifier(device):

    tvoc = device.property(int, 'TVOC', default=0)
    automatic_mode = device.property(bool, 'AutomaticMode', default=True)
    pm25 = device.property(int, 'PM25', default=0)
    filter_life = device.property(float, 'FilterLife', default=1)
    sleeping = device.property(bool, 'Sleeping', default=False)
    away = device.property(bool, 'Away', default=False)
    dog_mode = device.property(bool, 'DogMode', default=False)
    fan_mode = device.property(str, 'FanMode', default='Automatic')

    automatic_fan_speed = device.property(
        float, 'AutomaticFanSpeed', default=0.0
    )

    controls = device.property(
        float, 'Controls', default=0.0
    )

    fan_speed = device.property(
        float, 'FanSpeed', default=0.0
    )
    
    @automatic_mode.on_enable
    def automatic_mode_enabled():
        fan_mode.command = 'Automatic'

    @controls.on_command()
    def controls_command():
        fan_mode.command = 'Manual'
        automatic_mode.command = False

    @fan_mode.on_change(pass_context=True)
    def fan_mode_change(_, new):
        if new == 'automatic':
            fan_mode.update = 'Automatic'
        elif new == 'manual':
            fan_mode.update = 'Manual'

    @tvoc.on_change()
    @pm25.on_change()
    @sleeping.on_change()
    @away.on_change()
    @dog_mode.on_change()
    @controls.on_change()
    @fan_mode.on_change()
    def update():

        air_quality_perc = max(0.0, min(1.0, (pm25.value - 5.0) / 20.0))
        tvoc_ppm_perc = max(0.0, min(1.0, (tvoc.value - 150) / (1000.0 - 150.0)))

        speed = max(0, tvoc_ppm_perc, air_quality_perc)
        automatic_fan_speed.command = speed

        if filter_life.value < 0.05:
            fan_speed.command = 0
            controls.update = 0
            fan_mode.command = 'Automatic'
            return

        if fan_mode.value.lower() == 'manual':
            automatic_mode.command = False
            fan_speed.command = controls.value
            return

        if sleeping.value:
            speed = 0.5

        if speed < 0.05:
            speed = 0

        fan_speed.command = speed
        controls.update = speed

    return {
        automatic_fan_speed,
        automatic_mode,
        away,
        controls,
        dog_mode,
        fan_speed,
        filter_life,
        pm25,
        sleeping,
        tvoc
    }
