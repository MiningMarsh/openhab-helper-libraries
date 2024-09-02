import time
from .. import device
from .. import log


@device.as_device()
def TimedLatch(device):

    energized = device.property(bool, 'Energized', default=False)
    powered = device.property(bool, 'Powered', default=False)

    monitor = device.property(
        bool, 'Monitor', default=False
    )
    
    timeout = device.property(
        int, 'Timeout', default=300
    )

    last_activation = device.property(
        int, 'LastActivation', default=0
    )

    @timeout.on_change()
    @last_activation.on_change()
    @energized.on_change()
    def update():
        energized.command = time.time() - last_activation.value <= timeout.value

    @monitor.on_activate
    def monitor_activated():
        last_activation.command = time.time()
    
    return {
        energized,
        powered,
        monitor,
        timeout
    }
