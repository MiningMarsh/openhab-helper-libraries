from mmdev.device import as_device
from mmdev import rules


@as_device()
def Humidifier(device):
    automatic_target = device.property(float, 'AutomaticTarget', default=0.5)
    powered = device.property(bool, 'Powered', default=True)
    energized = device.property(bool, 'Energized', default=False)
    humidity = device.property(float, 'Humidity', default=0.5)

    @rules.register
    @humidity.on_change
    @automatic_target.on_change
    @powered.on_change
    def update():
        if not powered.value:
            energized.command = False
            return

        target = automatic_target.value

        if energized.value:
            if humidity.value > target:
                energized.command = False

        elif humidity.value < target - 0.05:
            energized.command = True

    return {
        automatic_target,
        powered,
        energized,
        humidity
    }
