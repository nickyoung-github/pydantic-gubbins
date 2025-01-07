from pydantic import ConfigDict, ValidationError
from pydantic_gubbins import BaseModel
import pytest
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


class Base(BaseModel):
    base_i: int
    base_s: str = FieldDescriptor("base_s")


class Derived1(Base):
    d1_i: int = FieldDescriptor(11)
    d1_s: str


class Derived2(Derived1):
    d2_i: int = FieldDescriptor(21)
    d2_s: str = FieldDescriptor("d2_s")


def test_basics():
    d2 = Derived2(d1_s="d1_s", base_i=1)
    assert d2.base_i == 1
    assert d2.base_s == "base_s"
    assert d2.d1_i == 11
    assert d2.d1_s == "d1_s"
    assert d2.d2_i == 21
    assert d2.d2_s == "d2_s"

    assert d2.__pydantic_descriptor_fields__ == {"base_s", "d1_i", "d2_i", "d2_s"}

    assert "base_i" in d2.__dict__
    assert "base_s" not in d2.__dict__
    assert "d1_i" not in d2.__dict__
    assert "d1_s" in d2.__dict__
    assert "d2_i" not in d2.__dict__
    assert "d2_s" not in d2.__dict__

    d2.base_i = -1
    d2.base_s = "s_base"

    assert d2.base_i == -1
    assert d2.base_s == "s_base"
    assert d2.__dict__["base_i"] == -1


def test_serialisation():
    d2 = Derived2(d1_s="d1_s", base_i=1)
    as_dict = d2.model_dump()
    assert all(as_dict[f] == getattr(d2, f) for f in d2.model_fields.keys())

    d2_new = Derived2.model_validate_json(d2.model_dump_json())
    assert d2_new == d2


def test_assignment_validation():
    b = Base(base_i=123)
    b.base_i = "123"  # Works as assignment does not perform validation

    class StrictBase(Base):
        model_config = ConfigDict(validate_assignment=True)

    sb = StrictBase(base_i=123)
    sb.base_i = 321

    with pytest.raises(ValidationError):
        sb.base_1 = "321"
