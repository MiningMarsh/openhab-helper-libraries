import scope


def suppress(function):
    try:
        return function()
    except:
        return None


def sanitize(value):
    if value is None:
        return value
    elif isinstance(value, scope.UnDefType):
        return None
    elif isinstance(value, scope.HSBType):
        return (
            float(str(value.getHue())),
            float(str(value.getSaturation())) / 100.0,
            float(str(value.getBrightness())) / 100.0
        )
    elif isinstance(value, scope.OnOffType):
        return value == scope.ON
    elif isinstance(value, scope.PercentType):
        return float(str(value)) / 100.0
    elif isinstance(value, scope.DecimalType):
        return float(str(value))
    elif isinstance(value, scope.StringType):
        return str(value)
    # Assume at this point that it is a QuantityType
    else:
        return float(str(value).split()[0])
