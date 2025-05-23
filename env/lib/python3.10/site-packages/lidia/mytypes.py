from typing import List, Tuple
from pydantic import BaseModel, Extra
from pydantic.utils import deep_update


# HACK: These classes rely on iteration through dict of fields in the order they were defined
#       So far observed to work in CPython, but isn't guaranteed by language implementations

class VectorModel(BaseModel):
    """Vector data to be serialized as array in SMOL"""

    def smol(self) -> List[float]:
        return [getattr(self, name) for name in self.__fields__]

    @classmethod
    def from_list(cls, values):
        return cls(**dict(zip(cls.__fields__, values)))

    def __add__(self, other):
        assert type(self) == type(other)
        copy = self.copy()
        for f in self.__fields__:
            setattr(copy, f, getattr(self, f) + getattr(other, f))
        return copy

    def __neg__(self):
        copy = self.copy()
        for f in self.__fields__:
            setattr(copy, f, -getattr(self, f))
        return copy

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        o = float(other)
        copy = self.copy()
        for f in self.__fields__:
            setattr(copy, f, getattr(self, f) * o)
        return copy

    def __truediv__(self, other):
        return self * (1 / other)


class IntFlagModel(BaseModel):
    """Data like `enum.IntFlag` to be serialized as int bits in SMOL"""

    def smol(self) -> List[int]:
        result = []
        for i, name in enumerate(self.__fields__):
            if i % 32 == 0:
                result.append(0)
            if getattr(self, name):
                result[i // 32] |= 1 << (i % 32)
        return result

    @classmethod
    def from_list(cls, flag_groups):
        assignment = {}
        for i, field in enumerate(cls.__fields__):
            assignment[field] = bool(flag_groups[i // 32] & (1 << (i % 32)))
        return cls(**assignment)


class NestingModel(BaseModel, extra=Extra.forbid):
    """Extension to `pydantic.BaseModel` allowing for updating with nested dictionary"""

    def updated(self, update_dict: dict[str, object]):
        """Construct new model, overriding values provided in nested dictionary

        The data is validated, both for type and not having keys undefined in the model"""

        # HACK: change new keys to old for the transitive period (pydantic validation_alias with AliasChoice didn't work)
        replacements: List[Tuple[str, Tuple[str, str]]] = [
            ('rpctask', ('ok_tolerance', 'correct_tolerance')),
            ('rpctask', ('warn_tolerance', 'warning_tolerance')),
            ('instruments', ('alt_multiplier', 'altitude_multiplier')),
            ('instruments', ('ralt_activation', 'radio_altimeter_activation')),
        ]
        for group, (new, old) in replacements:
            if group in update_dict and new in update_dict[group]:
                update_dict[group][old] = update_dict[group][new]
                del update_dict[group][new]

        new_dict = deep_update(self.dict(by_alias=True), update_dict)
        # return value is not annotated because it caused problems with type analysis for children
        return self.__class__(**new_dict)
