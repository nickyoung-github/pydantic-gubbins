from dataclasses import asdict, dataclass, fields, make_dataclass
from datetime import date
from pydantic import TypeAdapter, ValidationError
from pytest import raises
from typing import _SpecialForm, Callable, ParamSpec, TypeVar, Union, get_args, get_origin

P = ParamSpec("P")
R = TypeVar("R")


class TemplateBase:
    __concrete_type__: type
    __field_names__: set[str]
    __type_adaptor__: TypeAdapter

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __setattr__(self, key, value):
        if key not in self.__field_names__:
            raise AttributeError(f"{key} is not a valid attribue")

        if getattr(self, key) is not None:
            raise AttributeError(f"{key} cannot be re-assigned")

        self.__type_adaptor__.validator.validate_assignment(self, key, value, strict=True)

    @property
    def concrete(self):
        return TypeAdapter(self.__concrete_type__).validate_python(asdict(self))


class TemplateOf:
    def __getitem__(self, item: Callable[P, R]) -> Callable[P, R]:
        field_names = set()
        flds = []
        for fld in fields(item):
            typ = fld.type
            if get_origin(typ) is Union:
                typ = Union[get_args(typ) + (type(None),)]
            else:
                typ = Union[typ, type(None)]

            flds.append((fld.name, typ, None))
            field_names.add(fld.name)

        template_type = make_dataclass(
            f"Template{item.__name__}",
            flds,
            init=False,
            bases=(TemplateBase,),
            namespace={
                "__concrete_type__": item,
                "__field_names__": field_names,
                "__module__": item.__module__
            }
        )

        template_type.__type_adaptor__ = TypeAdapter(template_type)

        return template_type


Template = TemplateOf()


@dataclass(frozen=True, kw_only=True)
class Option:
    ticker: str
    strike: float
    expiry: date


option = Template[Option](ticker="TTF")
option.expiry = date(2025, 12, 31)

with raises(ValidationError):
    option.strike = "100."

with raises(ValidationError):
    option.concrete

option.strike = 100
print(repr(option.concrete))
