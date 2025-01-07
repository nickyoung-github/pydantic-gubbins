from dataclasses import is_dataclass
from frozendict import frozendict
from pydantic import BaseModel, Discriminator, GetCoreSchemaHandler, GetJsonSchemaHandler, Tag, WrapSerializer
from pydantic.json_schema import JsonSchemaValue
import pydantic_core.core_schema as core_schema
from typing import _SpecialForm, Annotated, Any, Iterable, TypeVar, Union as _Union, get_args, get_origin


TYPE_FIELD = "t_"

def get_type_name(typ: type) -> str:
    return getattr(typ, TYPE_FIELD, typ.__name__)


class UnionSchemaWithType:
    def __init__(self, types: tuple[type, ...]):
        self.__types = types

    def __get_pydantic_json_schema__(self,
                                     core_schema_: core_schema. CoreSchema,
                                     handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema_))

        for idx, ref in enumerate(json_schema["oneOf"]):
            defn = handler.resolve_ref_schema(ref)
            defn["properties"][TYPE_FIELD] = {"title": "Type", "enum": [get_type_name(self.__types[idx])]}

        return json_schema


@_SpecialForm
def DiscriminatedUnion(_cls, types: Iterable[type]):
    """
    :param _cls:
    :param types:
    :return: Annotated[Union[types], ...]

    A tagged union of types, using the class var TYPE_KEY as the tag name, falling back to class name, if not present
    """

    def add_tag_name(value, handler, _info) -> dict[str, Any]:
        return {**handler(value), TYPE_FIELD: get_type_name(type(value))}

    def get_tag_name(value) -> str:
        if isinstance(value, dict):
            return value.pop(TYPE_FIELD)

        return get_type_name(type(value))

    args = ()
    param_types = ()
    for typ in types:
        param_type = get_args(typ)[0] if get_origin(typ) is Annotated else typ
        if not issubclass(param_type, BaseModel) and not is_dataclass(param_type):
            raise RuntimeError(f"DiscriminatedUnion may only be used with BaseModel or dataclass types")
        args += (Annotated[typ, Tag(get_type_name(typ))],)
        param_types += (param_type,)

    return Annotated[_Union[args],
                     UnionSchemaWithType(param_types), WrapSerializer(add_tag_name), Discriminator(get_tag_name)]


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
        param_type = get_args(typ)[0] if get_origin(typ) is Annotated else typ
        if issubclass(param_type, BaseModel) or is_dataclass(param_type):
            model_types += (typ,)
        else:
            other_types += (typ,)

    if not model_types:
        return _Union[other_types]
    elif len(model_types) == 1:
        return _Union[other_types + model_types]
    else:
        discriminated_union = DiscriminatedUnion[model_types]

        if other_types:
            return _Union[Union[other_types], discriminated_union]
        else:
            return discriminated_union


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
