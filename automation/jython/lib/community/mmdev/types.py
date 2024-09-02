import collections
from core.jsr223.scope import UnDefType, QuantityType, DecimalType, PercentType, ON, OFF, OnOffType, HSBType, StringType
from java.lang import String


Type = collections.namedtuple(
    'Type', 
    'is_func to_func from_func'
)


_PRECISION = 2


def is_undefined(value):
    return isinstance(value, UnDefType)


def to_undefined(value):
    return UnDrfType()


def from_undefined(value):
    return None


def to_undefined(value):
    return UnDefType()


def from_undefined(value):
    return None


def is_string(value):
    return isinstance(value, StringType)


def to_string(value):
    return StringType(str(value))


def from_string(value):
    return str(value)


def is_quantity(value):
    return isinstance(value, QuantityType)


def to_quantity(value):
    return QuantityType(
        str(round(float(value), _PRECISION))
    )


def from_quantity(value):
    return round(value.doubleValue(), _PRECISION)


def is_decimal(value):
    return isinstance(value, DecimalType)


def to_decimal(value):
    return DecimalType(
        str(round(float(value), _PRECISION))
    )


def from_decimal(value):
    return round(value.doubleValue(), _PRECISION)


def is_percent(value):
    return isinstance(value, PercentType)


def to_percent(value):
    if value is False:
        value = 0.0
    if value is True:
        value = 1.0
    if value >= 1.0:
        value = 1.0
    if value <= 0.0:
        value = 0.0
    
    if value is not True:
        return PercentType(
            str(round(value * 100.0, _PRECISION))
        )


def from_percent(value):
    if value == OFF:
        return 0.0
    if value == ON:
        return 1.0
    return round(value.doubleValue() / 100.0, _PRECISION)


def is_color(value):
    return isinstance(value, HSBType)

def to_color(value):
    hue, saturation, brightness = value
    return HSBType(
        to_decimal(hue),
        to_percent(saturation),
        to_percent(brightness)
    )


def from_color(value):
    return (
        round(value.getHue().doubleValue(), _PRECISION),
        round(value.getSaturation().doubleValue() / 100.0, _PRECISION),
        round(value.getBrightness().doubleValue() / 100.0, _PRECISION)
    )


def is_onoff(value):
    return isinstance(value, OnOffType)


def to_onoff(value):
    if value:
        return ON
    return OFF


def from_onoff(value):
    return value == ON


TYPES = [
    Type(
        is_func=is_string,
        to_func=to_string,
        from_func=from_string
    ),
    Type(
        is_func=is_color,
        to_func=to_color,
        from_func=from_color
    ),
    Type(
        is_func=is_percent,
        to_func=to_percent,
        from_func=from_percent
    ),
    Type(
        is_func=is_decimal,
        to_func=to_decimal,
        from_func=from_decimal
    ),
    Type(
        is_func=is_quantity,
        to_func=to_quantity,
        from_func=from_quantity
    ),
    Type(
        is_func=is_onoff,
        to_func=to_onoff,
        from_func=from_onoff
    ),
    Type(
        is_func=is_undefined,
        to_func=to_undefined,
        from_func=from_undefined
    )
]


def is_equal(left_value, right_value):
    for is_func, _, from_func in TYPES:
        if is_func(left_value) and is_func(right_value):
            return from_func(left_value) == from_func(right_value)
    return False


def from_type(value):
    for is_func, _, from_func in TYPES:
        if is_func(value):
            return from_func(value)

    raise Exception('Unsupported item type: %s (%s)' % (type(value), type(value)))
