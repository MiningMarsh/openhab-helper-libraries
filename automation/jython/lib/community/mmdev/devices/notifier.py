import time
from .. import device
from .. import log


@device.as_device()
def Notifier(device):

    monitor = device.property(
        bool, 'Monitor', default=False
    )

    energized = device.property(
        bool, 'Energized', default=False
    )

    @monitor.on_activate
    def update():
        energized.command = True
        energized.command = False
    
    return {
        monitor,
        energized
    }
