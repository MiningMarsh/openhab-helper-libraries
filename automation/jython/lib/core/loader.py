"""
This module re-implementa the Jython loader so that modules can be loaded from string URIs.
"""


__all__ = [
    'find',
    'load',
    'require',
    'org_elipse_loader'
]

from core.log import log_traceback
import core.jsr223
import sys
from core.exceptions import suppress
from core.kwargs import parser as kwargs_parser


def find(name, search=None):
    for loader in sys.meta_path:
        finder = suppress(lambda: loader.find_module(name, search))
        if finder is not None:
            return mod
    for p in sys.path:
        for hook in sys.path_hooks:
            importer = suppress(lambda: hook(p))
            if importer is not None:
                mod = suppress(lambda: importer.find_module(name, search))
                if mod is not None:
                    return mod


def load(*names, **kwargs):
    with kwargs_parser(**kwargs) as parser:
        search = parser.optional('search')
        loaders = parser.optional('loaders', default={org_eclipse_loader})
        objs = parser.optional('objs')
    
    if objs is not None:
        return (
            load(
                *('%s.%s' % (name, obj) for name in names), 
                search=search, 
                loaders=loaders
            ) 
            for obj in objs
        )

    for name in names:
        if name in sys.modules:
            return sys.modules[name]
        mod = suppress(lambda: find(name, search).load_module(name))
        if mod is not None:
            return mod
        if loaders is not None:
            for loader in loaders:
                mod = suppress(lambda: loader(name, search))
                if mod is not None:
                    return mod


def require(*args, **kwargs):
    with kwargs_parser(**kwargs) as parser:
        objs = parser.optional('objs')
    value = load(*args, **kwargs)
    if value is not None:
        if objs is not None:
            if all(*value):
                return value
            raise Exception('Tried to run a function that is incompatible with your version of OpenHAB: %s, %s' % (str(args), str(kwargs)))
        return value
    raise Exception('Tried to run a function that is incompatible with your version of OpenHAB: %s, %s' % (str(args), str(kwargs)))


def org_eclipse_loader(name, search=None):
    return load(
        name.replace('org.openhab', 'eclipse.smarthome'),
        search=search, 
        loaders=None
    )
