from .. import device
import time


@device.as_device()
def TimedLatch(device, target=True, powered=True):

    powered = device.property(bool, 'Powered', default=powered)
    energized = device.property(bool, 'Energized', default=target)
    last_unlatched = device.property(int, 'LastUnlatched', default=time.time())
    timeout = device.property(int, 'Timeout', default=300)

    @energized.on_change(pass_context=True)
    def update_latch(_, new):
        if new != target:
            last_unlatched.command = time.time()

    @device.rule_engine.every_second
    def check_latch():
        if not powered.value:
            energized.command = not target
        elif energized.value != target and timeout.value < time.time() - last_unlatched.value:
            energized.command = target
        else:
            energized.command = not target

    return {
        energized,
        powered,
        timeout
    }
