from mmdev import device, rules


@device.as_device()
def AutomaticSwitch(device):
    
    energized = device.property(bool, 'Energized', default=False)
    powered = device.property(bool, 'Powered', default=False)
    mode = device.property(str, 'Mode', default='Automatic')
    controls = device.property(bool, 'Controls', default=False)
    monitor = device.property(bool, 'Monitor', default=False)

    @rules.register
    @powered.on_change
    @monitor.on_change
    def update():
        if not powered:
            energized.command = False
            return

        if str(mode.value).lower().strip() == 'automatic':
            energized.command = monitor.value
            controls.update = monitor.value
        else:
            energized.command = controls.value

    @rules.register
    @rules.pass_context
    @mode.on_change
    def mode_command(_, change):
        if change.lower().strip() == 'automatic':
            mode.update = 'Automatic'
        else:
            mode.update = 'Manual'
        update()

    @rules.register
    @controls.on_command
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
