__all__ = [
    "parser"
]
from contextlib import contextmanager
from core.log import log_traceback


class Parser(object):
    def __init__(self, **kwargs):
        self.__kwargs = kwargs
        self.__names = set()
        self.__grouped = set()
        self.__conflicting = set()
        self.__incompatible = set()
        self.__one_of = set()

    @log_traceback
    def __mark(self, name):
        if name in self.__names:
            raise Exception('Tried to mark kwarg argument twice!')
        self.__names.add(name)

    def optional(*names, **options):
        self, names = names[0], names[1:]
        if len(names) == 1:
            self.__mark(names[0])
            if names[0] in self.__kwargs:
                return self.__kwargs[names[0]]
            else:
                if 'default' in options:
                    return options['default']
                return None

        results = []
        for name in names:
            results.append(self.optional(name, **options))
        return results

    @log_traceback
    def required(*names):
        self, names = names[0], names[1:]

        if len(names) == 1:
            if names[0] not in self.__kwargs:
                raise Exception('Required key not passed to function: ' + names[0])
            self.__mark(names[0])
            return self.__kwargs[names[0]]

        results = []
        for name in names:
            results.append(self.required(name, **options))
        return results
            
    def grouped(*names):
        self, names = names[0], names[1:]
        self.__grouped.add(names)

    def conflicting(*names):
        self, names = names[0], names[1:]
        self.__conflicting.add(names)

    def incompatible(*names):
        self, names = names[0], names[1:]
        self.__incompatible.add(names)

    def one_of(*names):
        self, names = names[0], names[1:]
        self.__one_of.add(names)

    @log_traceback
    def finalize(self):
        if any(k not in self.__names for k in self.__kwargs.keys()):
            raise Exception('Function passed extra arguments: ' + str(self.__kwargs))

        for group in self.__grouped:
            if any(k not in self.__names for k in grouped) and any(k in self.__names for k in grouped):
                raise Exception('Group not satisfied: ' + str(group))

        for conflicting in self.__conflicting:
            if all(k in self.__names for k in conflicting):
                raise Exception('Conflict triggered: ' + str(conflict))

        for incompatible in self.__incompatible:
            if sum(1 if k in self.__names else 0 for k in incompatible) > 1:
                raise Exception('Conflict triggered: ' + str(conflict))

        for one_of in self.__one_of:
            if sum(1 if k in self.__names else 0 for k in one_of) == 0:
                raise Exception('Must provide at least one of these keywords: ' + str(one_of))


@contextmanager
def parser(**kwargs):
    parser = Parser(**kwargs)
    try:    
        yield parser
    finally:
        parser.finalize()
