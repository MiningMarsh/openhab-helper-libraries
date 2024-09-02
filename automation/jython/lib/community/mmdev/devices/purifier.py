from .. import device


@device.as_device()
def Purifier(device):

    tvoc = device.property(int, 'TVOC', default=0)
    automatic_mode = device.property(bool, 'AutomaticMode', default=0)
    automatic_speed = device.property(bool, 'AutomaticSpeed', default=0)
    pm25 = device.property(int, 'PM25', default=0)
    filter_life = device.property(float, 'FilterLife', default=1)
    sleeping = device.property(bool, 'Sleeping', default=False)
    away = device.property(bool, 'Away', default=False)
    dog_mode = device.property(bool, 'DogMode', default=False)

    automatic_fan_speed = device.property(
        float, 'AutomaticFanSpeed', default=0.0
    )

    controls = device.property(
        float, 'Controls', default=0.0
    )

    fan_speed = device.property(
        float, 'FanSpeed', default=0.0
    )
    
    @automatic_mode.on_activate
    def automatic_mode_activated():
        automatic_speed.command = True

    @fan_speed.on_command()
    def manual_command():
        automatic_speed.command = False
        automatic_mode.command = False

    @tvoc.on_change()
    @pm25.on_change()
    @automatic_speed.on_change()
    @sleeping.on_change()
    @away.on_change()
    @dog_mode.on_change()
    @fan_speed.on_change()
    @controls.on_change()
    def update():

        if filter_life.value < 0.15:
            fan_speed.command = 0
            controls.update = 0
        
        air_quality_perc = 1.0 - max(0.0, min(1.0, (pm25.value - 5.0) / 20.0))
        tvoc_ppm_perc = 1.0 - max(0.0, min(1.0, tvoc.value / 12000.0))

        speed = max(0, 1.0 - min(tvoc_ppm_perc, air_quality_perc))
        automatic_fan_speed.command = speed

        if not automatic_speed.value:
            fan_speed.command = controls.value
            return

        speed = max(0.5, speed)
        if sleeping.value:
            speed = min(0.33, speed)

        if away.value or dog_mode.value and device.room_name.lower().replace(' ', '_') == 'livingroom':
            speed = 1

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
