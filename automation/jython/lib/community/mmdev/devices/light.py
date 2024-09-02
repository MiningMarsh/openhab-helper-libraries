from org.openhab.core.library.unit import Units
from community.mmdev.device import as_device


@as_device()
def Light(device):

    color = device.property(
        tuple, 'Color', default=(0,0,0), force=True, 
    )

    controls = device.property(
        tuple, 'Controls', default=(0,0,0), force=True,
        metadata={'ga': ('Light', {
            'roomHint': device.room_name,
            'name': device.device_name,
            'colorTemperatureRange': '2000,6500'
        })}
    )

    color_temperature = device.property(
        int, 'ColorTemperature', default=2000, force=True, unit=Units.KELVIN
    )

    automatic_mode = device.property(
        bool, 'AutomaticMode', default=True
    )

    away = device.property(
        bool, 'Away', default=False
    )

    dog_mode = device.property(
        bool, 'DogMode', default=False
    )

    automatic_brightness_mode = device.property(
        bool, 'AutomaticBrightnessMode', default=True
    )

    automatic_color_temperature_mode = device.property(
        bool, 'AutomaticColorTemperatureMode', default=True
    )

    motion_detected = device.property(
        bool, 'MotionDetected', default=False
    )

    automatic_color_temperature = device.property(
        int, 'AutomaticColorTemperature', default=6500
    )

    automatic_brightness = device.property(
        float, 'AutomaticBrightness', default=1
    )

    sleeping = device.property(
        bool, 'Sleeping', default=False
    )

    @automatic_brightness.on_change()
    @automatic_brightness_mode.on_change()
    @automatic_color_temperature.on_change()
    @automatic_color_temperature_mode.on_change()
    @away.on_change()
    @controls.on_change()
    @dog_mode.on_change()
    @motion_detected.on_change()
    @sleeping.on_change()
    def update():
        h, s, b = controls.value

        brightness = (
            automatic_brightness.value
            if automatic_brightness_mode.value
            else b
        )
        
        if device.room_name in {'Bathroom'}:
            brightness = max(0.33, brightness)

        if away.value:
            brightness = 0

        if dog_mode.value and device.room_name == 'Living Room':
            brightness = 1

        power = (
            (motion_detected.value
             or not sleeping.value
             or device.room_name in {'Bathroom'})
            and device.room_name not in {'Closet'}
        )

        if not power:
            color.command = False
        elif automatic_color_temperature_mode.value:
            color.command = brightness
            color_temperature.command = max(2000, min(6500, automatic_color_temperature.value))
            controls.update = color.value
        else:
            color.command = (
                h, s,
                automatic_brightness.value
                if automatic_brightness_mode.value
                else b
            )
            controls.command(color.value, force=True)

    @automatic_mode.on_activate
    def automatic_mode_command():
        automatic_brightness_mode.command = True
        automatic_color_temperature_mode.command = True

    @automatic_brightness_mode.on_deactivate
    @automatic_color_temperature_mode.on_deactivate
    def automatic_modes_command():
        automatic_mode.command = False

    @controls.on_command(pass_context=True)
    def controls_command(value):
        automatic_mode.command = False
        if isinstance(value, float) or isinstance(value, bool):
            automatic_brightness_mode.command = False
        else:
            automatic_color_temperature_mode.command = False
        update()

    update()
    return {
        automatic_brightness,
        automatic_color_temperature,
        automatic_mode,
        away,
        controls,
        dog_mode,
        motion_detected,
        sleeping
    }
