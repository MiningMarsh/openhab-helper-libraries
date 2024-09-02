from .. import device

@device.as_device()
def Inverter(device):

    monitor = device.property(
        bool, 'Monitor', default=False
    )

    energized = device.property(
        bool, 'Energized', default=False
    )

    @monitor.on_change(pass_context=True)
    def update(_, new):
        energized.command = not new
    
    return {
        monitor,
        energized
    }
