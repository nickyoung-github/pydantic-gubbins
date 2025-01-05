from pydantic_gubbins import BaseModel
from typing import Any

_field_descriptor_undefined = object()


class FieldDescriptor:
    """ Example descriptor, just to show storage somewhere other than __dict__ """

    def __init__(self, default: Any = _field_descriptor_undefined):
        self.__default = default
        self.__name = None
        self.__values = {}

    def __get__(self, instance, owner):
        if instance is not None:
            try:
                return self.__values[id(instance)][self.__name]
            except KeyError:
                pass

        if self.__default is _field_descriptor_undefined:
            raise AttributeError

        return self.__default

    def __set__(self, instance, value):
        self.__values.setdefault(id(instance), {})[self.__name] = value

    def __set_name__(self, owner, name):
        self.__name = name



class Foo(BaseModel):
    s: str
    i: int = FieldDescriptor(-1)
