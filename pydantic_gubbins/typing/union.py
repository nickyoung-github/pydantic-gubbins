from dataclasses import is_dataclass
from frozendict import frozendict
from pydantic import BaseModel, Discriminator, GetCoreSchemaHandler, GetJsonSchemaHandler, Tag, WrapSerializer
from pydantic.json_schema import JsonSchemaValue
import pydantic_core.core_schema as core_schema
from typing import _SpecialForm, Annotated, Any, Iterable, TypeVar, Union as _Union, get_args, get_origin


TYPE_FIELD = "t_"


class UnionSchemaWithType:
    @classmethod
    def __get_pydantic_json_schema__(cls,
                                     core_schema_: core_schema. CoreSchema,
                                     handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema_))

        for ref in json_schema["oneOf"]:
            defn = handler.resolve_ref_schema(ref)
            defn["properties"][TYPE_FIELD] = {"title": "Type", "type": "string"}

        return json_schema


def get_type_name(typ: type) -> str:
    return getattr(typ, TYPE_FIELD, typ.__name__)


def __add_tag_name(value, handler, _info) -> dict[str, Any]:
    return {**handler(value), TYPE_FIELD: get_type_name(type(value))}


def __get_tag_name(value) -> str:
    if isinstance(value, dict):
        return value.pop(TYPE_FIELD)

    return get_type_name(type(value))


@_SpecialForm
def DiscriminatedUnion(_cls, types: Iterable[type]):
    """
    :param _cls:
    :param types:
    :return: Annotated[Union[types], ...]

    A tagged union of types, using tge class var TYPE_KEY as the tag name, falling back to class name, if not present
    """
    args = ()
    for typ in types:
        test_typ = get_args(typ)[0] if get_origin(typ) is Annotated else typ
        if not issubclass(test_typ, BaseModel) and not is_dataclass(test_typ):
            raise RuntimeError(f"DiscriminatedUnion may only be used with BaseModel or dataclass types")
        args += (Annotated[typ, Tag(get_type_name(typ))],)

    return Annotated[_Union[args], UnionSchemaWithType, WrapSerializer(__add_tag_name), Discriminator(__get_tag_name)]


@_SpecialForm
def SubclassOf(_cls, param_type: type):
    """
    :param _cls:
    :param param_type:
    :return:  Annotated[Union[...], ...]

    A discriminated union of the all the subclasses (recursively generated) of param_type
    """
    subclasses = set()
    stack = [param_type]
    while stack:
        subclass = stack.pop()
        subclasses.add(subclass)
        stack.extend(subclass.__subclasses__())

    return DiscriminatedUnion[subclasses]


@_SpecialForm
def Union(_cls, types: Iterable[type]):
    """
    :param _cls:
    :param types:
    :return: Union[types]

    A union of types. If more than one BaseModel or dataclass type is present, we will return a union of
    1. union of model types, 2. union of non-model types
    """
    model_types = ()
    other_types = ()

    for typ in types:
        test_typ = get_args(typ)[0] if get_origin(typ) is Annotated else typ
        if issubclass(test_typ, BaseModel) or is_dataclass(test_typ):
            model_types += (typ,)
        else:
            other_types += (typ,)

    if not model_types:
        return _Union[other_types]
    elif len(model_types) == 1:
        return _Union[other_types + model_types]
    else:
        discrinated_union = DiscriminatedUnion[model_types]

        if other_types:
            return _Union[Union[other_types], discrinated_union]
        else:
            return discrinated_union


class FrozenDictSchema:
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        def validate_from_dict(d: dict | frozendict) -> frozendict:
            return frozendict(d)

        frozendict_schema = core_schema.chain_schema(
            [
                handler.generate_schema(dict[*get_args(source_type)]),
                core_schema.no_info_plain_validator_function(validate_from_dict),
                core_schema.is_instance_schema(frozendict)
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=frozendict_schema,
            python_schema=frozendict_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(dict)
        )


_K = TypeVar('_K')
_V = TypeVar('_V')
FrozenDict = Annotated[frozendict[_K, _V], FrozenDictSchema]


__all__ = (
    TYPE_FIELD,
    DiscriminatedUnion,
    FrozenDict,
    SubclassOf,
    Union
)
