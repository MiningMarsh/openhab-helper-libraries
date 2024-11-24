from .. import device


@device.as_device()
def AutomaticSwitch(device):
    
    energized = device.property(bool, 'Energized', default=False)
    powered = device.property(bool, 'Powered', default=False)
    mode = device.property(str, 'Mode', default='Automatic')
    controls = device.property(bool, 'Controls', default=False)
    monitor = device.property(bool, 'Monitor', default=False)

    @powered.on_change()
    @monitor.on_change()
    def update():
        if not powered:
            energized.command = False
            return

        if mode.value.lower().strip() == 'automatic':
            energized.command = monitor.value
            controls.update = monitor.value
        else:
            energized.command = controls.value

    @mode.on_change(pass_context=True)
    def mode_command(_, change):
        if change.lower().strip() == 'automatic':
            mode.update = 'Automatic'
        else:
            mode.update = 'Manual'
        update()

    @controls.on_command()
    def controls_command():
        mode.command = 'Manual'
        update()

    update()

    return {
        energized,
        powered,
        monitor,
        controls,
        mode
    }
