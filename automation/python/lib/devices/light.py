import math

from .util.kelvintohsb import kelvin_to_hsb

from mmdev import device, rules
from mmdev.utils import sanitize


@device.as_device()
def Light(device):

    color = device.property(
        tuple, 'Color', default=(0,0,0) 
    )

    controls = device.property(
        tuple, 'Controls', default=(0,0,0),
        metadata={'ga': ('Light', {
            'roomHint': device.room_name,
            'name': device.device_name,
            'colorTemperatureRange': '2000,6500'
        })}
    )

    buffer = device.property(
        tuple, 'Buffer', default=(0,0,0)
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

    automatic_power_mode = device.property(
        bool, 'AutomaticPowerMode', default=True
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
        float, 'AutomaticBrightness', default=1.0
    )

    automatic_power = device.property(
        bool, 'AutomaticPower', default=True
    )

    sleeping = device.property(
        bool, 'Sleeping', default=False
    )

    @rules.register
    @motion_detected.on_change
    @sleeping.on_change
    def update_power():
        automatic_power.command = (
            not sleeping.value
            or motion_detected.value
            or device.room_name == 'Bathroom'
        )

    @rules.register
    @automatic_brightness.on_change
    @automatic_brightness_mode.on_change
    @automatic_color_temperature.on_change
    @automatic_color_temperature_mode.on_change
    @automatic_power_mode.on_change
    @automatic_power.on_change
    @motion_detected.on_change
    @sleeping.on_change
    @buffer.on_change
    def update():
        h, s, b = buffer.value
        if automatic_brightness_mode.value:
            b = automatic_brightness.value

        if automatic_power_mode.value:
            auto = automatic_power.value
            if auto and device.room_name == 'Bathroom':
                b = max(0.333, b)
            elif not auto:
                b = 0.0

        if automatic_color_temperature_mode.value:
            hsb = sanitize(kelvin_to_hsb(automatic_color_temperature.value))
            h, s = hsb[0], hsb[1]

        if b == 0.0:
            color.command = False
        else:
            color.command = (h, s, b)
        controls.update = buffer.value

    @rules.register
    @automatic_mode.on_activate
    def automatic_mode_command():
        automatic_brightness_mode.command = True
        automatic_color_temperature_mode.command = True
        automatic_power_mode.command = True

    @rules.register
    @automatic_brightness_mode.on_deactivate
    @automatic_color_temperature_mode.on_deactivate
    @automatic_power_mode.on_deactivate
    def automatic_modes_command():
        automatic_mode.command = False

    @rules.register
    @rules.pass_context
    @controls.on_command
    def controls_command(value):
        automatic_power_mode.command = False
        if isinstance(value, bool) and value is True:
            if color.value[2] != 1.0:
                automatic_brightness_mode.command = False
        elif not isinstance(value, bool):
            if isinstance(value, float) or isinstance(value, int):
                automatic_brightness_mode.command = False
            elif isinstance(value, tuple) or isinstance(value, list):
                automatic_color_temperature_mode.command = False
        buffer.command = value

    return {
        automatic_brightness,
        automatic_color_temperature,
        automatic_mode,
        away,
        dog_mode,
        motion_detected,
        sleeping
    }
