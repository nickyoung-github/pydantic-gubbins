from frozendict import frozendict
from pydantic import GetCoreSchemaHandler
import pydantic_core.core_schema as core_schema
from typing import Annotated, TypeVar


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