from pydantic import BaseModel, TypeAdapter
from typing import Union as _Union, get_args, get_origin

from pydantic_gubbins.typing import DiscriminatedUnion, SubclassOf, Union


class Base(BaseModel):
    i: int = 123


class Derived1(Base):
    s: str = "hello"


class Derived2(Derived1):
    f: float = 3.14159


class Outer(BaseModel):
    name: str
    contents: SubclassOf[Base]


def test_subclass_of():
    o = Outer(name="outer", contents=Derived2())
    as_dict = o.model_dump()
    assert as_dict["contents"]["t_"] == "Derived2"

    json_schema = o.model_json_schema()
    assert "t_" in json_schema["$defs"]["Base"]["properties"]
    assert "t_" in json_schema["$defs"]["Derived1"]["properties"]
    assert "t_" in json_schema["$defs"]["Derived2"]["properties"]

    o_new = Outer.model_validate_json(o.model_dump_json())
    assert o == o_new


def test_mixed_union():
    mixed_union1 = Union[int, Base, Derived1]
    args = get_args(mixed_union1)
    assert get_origin(mixed_union1) is _Union
    assert len(args) == 2
    assert args[0] is int
    assert args[1] is DiscriminatedUnion[Base, Derived1]

    adapter1 = TypeAdapter(mixed_union1)
    assert adapter1.validate_json(adapter1.dump_json(1)) == 1
    assert adapter1.validate_json(adapter1.dump_json(Base())) == Base()
    assert adapter1.validate_json(adapter1.dump_json(Derived1())) == Derived1()

    mixed_union2 = Union[int, Base]
    args = get_args(mixed_union2)
    assert get_origin(mixed_union2) is _Union
    assert len(args) == 2
    assert args[0] is int
    assert args[1] is Base

    adapter2 = TypeAdapter(mixed_union2)
    assert adapter2.validate_json(adapter1.dump_json(1)) == 1
    assert adapter2.validate_json(adapter1.dump_json(Base())) == Base()
