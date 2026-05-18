import time


from mmdev.device import as_device
from mmdev.timer import Timer
from mmdev import rules


@as_device()
def Lock(device, timeout=300.0):
    energized = device.property(bool, 'Energized', default=True)
    last_unlocked = device.property(int, 'LastUnlocked', default=0)
    timer = None

    def lock():
        energized.command = True

    @rules.register
    @energized.on_enable
    def locked():
        nonlocal timer
        if timer is not None:
            timer.cancel()
            timer = None

    @rules.register
    @energized.on_disable
    def unlocked():
        nonlocal timer
        last_unlocked.command = time.time()
        timer = Timer.create(timeout, lock, old_timer=timer)

    if not energized.value:
        elapsed = time.time() - last_unlocked.value
        if elapsed >= timeout:
            lock()
        else:
            timer = Timer.create(timeout - elapsed, lock)

    return {energized}
