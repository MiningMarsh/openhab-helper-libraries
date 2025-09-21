import math

from org.openhab.core.library.unit import Units
from org.openhab.core.util import ColorUtil

from community.mmdev.util.kelvintohsb import kelvin_to_hsb

from .. import types
from .. import device
from .. import log


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
        float, 'AutomaticBrightness', default=1
    )

    # User to travk brightness when loght ia turned off, allows brightness restore on turn on.
    last_brightness = device.property(
        float, 'LastBrightness', default=1.0
    )

    sleeping = device.property(
        bool, 'Sleeping', default=False
    )

    @automatic_brightness.on_change()
    @automatic_brightness_mode.on_change()
    @automatic_color_temperature.on_change()
    @automatic_color_temperature_mode.on_change()
    @automatic_power_mode.on_change()
    @motion_detected.on_change()
    @sleeping.on_change()
    def update():
        h, s, b = controls.value
        if device.room_name == 'Bedroom':
            log.LOGGER.error('h, s, b = (%s, %s, %s)' % (h, s, b))

        min_brightness = 0.10 if sleeping.value else 0.15
        if device.room_name == 'Bathroom':
            min_brightness = 0.33 if sleeping.value else 0.5

        brightness = (
            min_brightness + ((1 - min_brightness) * automatic_brightness.value)
            if automatic_brightness_mode.value
            else b
        )

        if device.room_name == 'Bedroom':
            log.LOGGER.error('brightness = %s' % brightness)

        if sleeping.value:
            automatic_power = (
                device.room_name == 'Bathroom'
                or motion_detected.value
            )
        else:
            automatic_power = device.room_name != 'Closet'

        if device.room_name == 'Bedroom':
            log.LOGGER.error('automatic_power = %s' % automatic_power)

        if automatic_power_mode.value and not automatic_power:
            brightness = 0.0

        elif automatic_color_temperature_mode.value:
            h, s, _ = types.from_color(
                kelvin_to_hsb(
                    automatic_color_temperature.value
                )
            )

        if color.value[2] == 0 and brightness > 0:
            color.command = True
        color.command = (h, s, brightness)

        if device.room_name == 'Bedroom':
            log.LOGGER.error('command => (%s, %s, %s)' % (h, s, brightness))

        controls.update = color.value
        if color.value[2] > 0:
            last_brightness.command = color.value[2]

    @automatic_mode.on_activate
    def automatic_mode_command():
        automatic_brightness_mode.command = True
        automatic_color_temperature_mode.command = True
        automatic_power_mode.command = True

    @automatic_brightness_mode.on_deactivate
    @automatic_color_temperature_mode.on_deactivate
    @automatic_power_mode.on_deactivate
    def automatic_modes_command():
        automatic_mode.command = False

    @controls.on_command(pass_context=True)
    def controls_command(value):
        automatic_mode.command = False
        if value is True:
            automatic_power_mode.command = False
            controls.command = last_brightness.value

        elif value is False:
            automatic_power_mode.command = False
            controls.command = 0

        elif isinstance(value, float) or isinstance(value, int):
            automatic_brightness_mode.command = False
            if value > 0:
                last_brightness.command = value

        elif isinstance(value, tuple) or isinstance(value, list):
            automatic_color_temperature_mode.command = False

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
