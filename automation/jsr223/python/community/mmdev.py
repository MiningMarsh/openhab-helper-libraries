from core.items import remove_item
from core.log import log_traceback
from core.metadata import get_metadata

from community.mmdev.items import all_items
from community.mmdev.log import LOGGER
from community.mmdev.rules import cron

import time


_BOOT = time.time()


def gc(item):
    remove_item(item)
    LOGGER.info('Garbage Collected: %s' % item)


@cron('0 * * ? * * *')
@log_traceback
def item_reaper():
    if time.time() - _BOOT < 5 * 60:
        return

    for item in all_items():
        if not item.startswith('MMDEV_') or item == 'MMDEV_BOOT':
            continue

        metadata = get_metadata(item, 'mmdev')
        try:
            valid = (
                metadata is not None
                and time.time() - float(metadata.value) < 5 * 60
            )
            if not valid:
                gc(item)
        except:
                gc(item)
