class _Sampler(object):
    def __init__(self, initial, samples=60):
        self.__samples = [initial] * samples
        self.__total = initial * samples
        self.__index = 0

    def __call__(self, sample):
        self.__total += sample - self.__samples[self.__index]
        self.__samples[self.__index] = sample
        self.__index += 1
        if self.__index == len(self.__samples):
            self.__index = 0

        return self.__total / len(self.__samples)

sampler = _Sampler
