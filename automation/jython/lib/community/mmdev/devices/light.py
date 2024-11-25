import math

from org.openhab.core.library.unit import Units
from org.openhab.core.util import ColorUtil

from community.mmdev.util.kelvintohsb import kelvin_to_hsb

from .. import types
from .. import device


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
    @dog_mode.on_change()
    @motion_detected.on_change()
    @sleeping.on_change()
    def update():
        h, s, b = controls.value

        min_brightness = 0.5 if sleeping.value else 0.15
        if not away.value and automatic_brightness_mode.value and device.room_name in {'Bathroom'}:
            min_brightness = 0.33

        brightness = (
            min_brightness + ((1 - min_brightness) * automatic_brightness.value)
            if automatic_brightness_mode.value
            else b
        )
        
        power = (
            not away.value 
            or (dog_mode.value and device.room_name == 'Bedroom')
        ) and (
            motion_detected.value
            or not sleeping.value
            or device.room_name == 'Bathroom'
            or (away.value and dog_mode.value and device.room_name == 'Bedroom')
        ) and (
            device.room_name != 'Closet'
        )
        
        if automatic_brightness_mode.value:
            brightness = automatic_brightness.value if power else 0

        if automatic_color_temperature_mode.value:
            if brightness > 0:
                h, s, _ = types.from_color(
                    kelvin_to_hsb(
                        automatic_color_temperature.value
                    )
                )

                color.command = (h, s, brightness)
                controls.update = color.value
            else:
                color.command = False
        else:
            if brightness > 0:
                color.command = (h, s, brightness)
            else:
                color.command = False
        controls.update = color.value

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
        if isinstance(value, float) or isinstance(value, int) or isinstance(value, bool):
            automatic_brightness_mode.command = False
        elif isinstance(value, tuple) or isinstance(value, list):
            automatic_color_temperature_mode.command = False
        else:
            automatic_brightness_mode.command = False
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
