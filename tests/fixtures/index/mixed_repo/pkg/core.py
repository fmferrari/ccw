from .helpers import helper_value


class PublicThing:
    pass


def build():
    return helper_value()


def _private():
    return None
