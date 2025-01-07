from _ctypes import Py_DECREF, Py_INCREF
from ctypes import POINTER, pythonapi, py_object
from typing import Any


class DictDescriptor:
    __obj_dict_ptr = None

    @classmethod
    def __dict_ptr(cls):
        if cls.__obj_dict_ptr is None:
            dict_ptr = pythonapi._PyObject_GetDictPtr
            dict_ptr.argtypes = (py_object,)
            dict_ptr.restype = POINTER(py_object)
            cls.__obj_dict_ptr = dict_ptr

        return cls.__obj_dict_ptr

    def __get__(self, instance, owner) -> dict[str, Any]:
        return self.__dict_ptr()(instance).contents.value

    def __set__(self, instance, value: dict[str, Any]):
        dict_contents = self.__dict_ptr()(instance).contents
        prev = dict_contents.value if dict_contents else None
        typ = type(instance)
        descriptor_values = {}
        current = {}

        for key, field_value in value.items():
            try:
                typ_value = object.__getattribute__(typ, key)
                if hasattr(typ_value, "__get__"):
                    descriptor_values[key] = field_value
                else:
                    current[key] = field_value
            except AttributeError:
                current[key] = field_value

        Py_INCREF(current)
        dict_contents.value = current

        if prev is not None:
            Py_DECREF(prev)

        instance.__set_descriptor_values__(descriptor_values)
