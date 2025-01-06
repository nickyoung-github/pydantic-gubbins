from functools import cached_property
from itertools import chain
from pydantic import BaseModel as _BaseModel, SerializerFunctionWrapHandler, model_serializer
from pydantic._internal._model_construction import ModelMetaclass as _ModelMetaClass
from typing import Any, ClassVar

from .descriptors import DictDescriptor


class ModelMetaclass(_ModelMetaClass):
    def __new__(cls, cls_name: str, bases: tuple[type[Any], ...], namespace: dict[str, Any], **kwargs):
        descriptors = {}

        for base in bases:
            if issubclass(base, _BaseModel):
                for name in getattr(base, "__pydantic_descriptor_fields__", ()):
                    descriptors[name] = object.__getattribute__(base, name)

        for name, typ in namespace.get("__annotations__", {}).items():
            value = namespace.get(name)
            if hasattr(value, "__get__") and not isinstance(value, (property, cached_property)):
                descriptors[name] = value

        namespace["__pydantic_descriptor_fields__"] = frozenset(descriptors.keys())
        if descriptors:
            namespace["__dict__"] = DictDescriptor()

        ret = super().__new__(cls, cls_name, bases, namespace, **kwargs)

        if descriptors:
            # We need this step as collect_model_fields() deletes descriptors
            for name, descriptor in descriptors.items():
                descriptor.__set_name__(ret, name)

                try:
                    ret.model_fields[name].default = descriptor.__get__(None, ret)
                except AttributeError:
                    pass

                setattr(ret, name, descriptor)

        return ret

class BaseModel(_BaseModel, metaclass=ModelMetaclass):
    __pydantic_descriptor_fields__: ClassVar[frozenset[str]]

    def __setattr__(self, key, value):
        if key in self.__pydantic_descriptor_fields__:
            # BaseModel overrides __setattr__ and calls self.__dict__[key] = value
            object.__setattr__(self, key, value)
        else:
            super().__setattr__(key, value)

    def __getstate__(self):
        return {**super().__getstate__(), "__descriptor_items__": self.__descriptor_items()}

    def __setstate__(self, state):
        super().__setstate__(state)
        for key, value in state.get("__descriptor_items__", ()):
            object.__setattr__(self, key, value)

    def __eq__(self, other):
        return super().__eq__(other) and\
            all(v1 == v2 for (_, v1), (_, v2) in zip(self.__descriptor_items(), other.__descriptor_items()))

    @model_serializer(mode='wrap')
    def include_descriptors(self, handler: SerializerFunctionWrapHandler) -> Any:
        return {**handler(self), **dict(self.__descriptor_items())}

    def __repr_args__(self):
        yield from (kv for kv in chain(self.__descriptor_items(), super().__repr_args__()))

    def __descriptor_items(self):
        yield from ((fld, getattr(self, fld)) for fld in self.__pydantic_descriptor_fields__)
