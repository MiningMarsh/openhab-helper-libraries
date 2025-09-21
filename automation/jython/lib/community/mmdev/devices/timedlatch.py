from .. import device
import time


@device.as_device()
def TimedLatch(device, latched=True):

    powered = device.property(bool, 'Powered')
    energized = device.property(bool, 'Energized', default=latched)
    monitor = device.property(bool, 'Monitor', default=not latched)
    last_unlatched = device.property(int, 'LastUnlatched', default=time.time())
    timeout = device.property(int, 'Timeout', default=300)

    @monitor.on_change(pass_context=True)
    def monitor_change(_, new):
        if not powered.value:
            last_unlatched.command = 0
        elif new == latched:
            energized.command = latched
        else:
            last_unlatched.command = time.time()

    @device.rule_engine.every_second
    def check_latch():
        unlatch = not powered.value or (
            monitor.value != latched 
            and energized.value == latched 
            and timeout.value < time.time() - last_unlatched.value
        )

        if unlatch:
            energized.command = not latched

    return {
        energized,
        powered,
        timeout
    }
