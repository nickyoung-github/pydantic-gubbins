# pydantic-gubbins

# Table of Contents
1. [Overview](#Overview)
2. [Typing](#Typing)
   1. [DiscriminatedUnion](#DiscriminatedUnion)
   2. [SubclassOf](#SubclassOf)
   3. [Union](#Union)
   4. [FrozenDict](#FrozenDict)
3. [Descriptor Support](#Descriptor-Support)


## Overview

This project contains various utils for working with `pydantic`.

## Typing

### DiscriminatedUnion

A common pattern `pydantic` users encounter is how to serialise/deserialise a field whose type is a union of `BaseModel`
types. This improved in `pydantic` v2 and various ways of implementing a discriminated union are detailed
[here](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions-with-str-discriminators).
However, this approach is a bit unsatisfying as:

- One is forced to explicitly implement a literal for each affected type
- The type literal will be serialised regardless of whether it's needed or not. E.g, if there is a field explicitly
of such a type (and not a union), the type literal will still be serialised

Stack Overflow and other forums have many long discussions on this topic, without apparently offering a solution, so
I have included my own implementation of `DiscriminatedUnion`. What it does:

1. Creates tagged union of the types: `Union[Annotated[t1, Tag("t1")], Annotated[t1, Tag("t2")], ...]`
2. Adds a `WrapSerializer` to include the tag name in the serialised output
3. Adds a `Discrimator` with a callable to retrieve the tag name from the serialised form
4. Uses the type's `__name__` by default but `type.TYPE_KEY` if present

### SubclassOf

`SubclassOf` takes a single type as a parameter and returns a `DiscriminatedUnion` of all the (recursive) subclasses
of that type

### Union

This can be used in place of `typing.Union`. It converts unions of `BaseModel` and `dataclass` types into a
`DiscriminatedUnion`. It also separates such "model" types from other types. In the event that both are encounted,
it returns `Union[Union[<other types>], DiscriminatedUnion[<model types>]]`

### FrozenDict

I found this implementation (and I can't remember where!) and included it. This is because I have some upcoming changes
which will convert collection types into immutable equivalents, to be combined with frozen models.


## Descriptor Support

`pydantic` does not support using descriptors for model fields. I have raised an
[issue](https://github.com/pydantic/pydantic/issues/11148) for this and submitted PRs for
[pydantic](https://github.com/pydantic/pydantic/pull/11176) (some further discussion on that thread) and
[pydantic-core](https://github.com/pydantic/pydantic-core/pull/1592) but the maintainers are correct in that the whole
descriptor issue really needs more discussion.

In the interim, this project supplies an implementation of `BaseModel`, which can be used in
place of the standard pydantic offering and which supports descriptors for model fields. Absent descriptor fields,
it will perform exactly as the original. It is not a large amount of code and the changes are summarised below.
The intent of these changes is the descriptor model fields should behave as closely as possible to [descriptors in
dataclasses](https://docs.python.org/3/library/dataclasses.html#descriptor-typed-fields).
Please note that `property` or `cached_property` passed as annotations will be ignored. This is because `pydantic`
already has special-case logic for them.

1. The metaclass adds the descriptors onto the the returned type, calls `__set_name__` on them,
and populates `__pydantic_descriptor_fields__`
2. The methods on `BaseModel` which access `__dict__` directly have been overridden to extend their functionality
to include descriptor fields
3. Access to `__dict__` itself is now controlled by a descriptor. This implementation is rather low-level and possibly
inadvisable. The same result might be achieved by using a model validator, however, there are many places
in `pydantic` and `pydantic-core` where `__dict__` is accessed directly and I'm not convinced all would be covered by
a validator

Using the `BaseModel` supplied by this project, the below works:

```py
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
```



