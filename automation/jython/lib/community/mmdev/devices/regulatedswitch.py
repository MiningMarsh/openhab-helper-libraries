import time
from .. import device
from .. import log


@device.as_device()
def Regulator(device):

    energized = device.property(bool, 'Energized', default=False)
    monitor = device.property(bool, 'Powered', default=False)
    cooldown_period = device.property(int, 'CooldownPeriod', default=300)
    duty_period = device.property(int, 'DutyPeriod', default=300)
    last_transition = device.property(int, 'LastTransition', default=time.time())

    @energized.on_change()
    def update_last_transition():
        last_transition.command = time.time()

    @device.rule_engine.every_second
    def update():
        if energized.value == monitor.value
            return

        now = time.time()
        if not energized.value and target and (now - last_transition.value >= cooldown_period.value):
            energized.command = True
        elif energized.value and not target and now - last_transition.value >= duty_period.value:
            energized.command = False
    
    update()

    return {
        energized,
        monitor
    }
