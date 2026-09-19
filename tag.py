# -*- coding: utf-8 -*-
# pylint: disable=undefined-variable,used-before-assignment,too-many-function-args,access-member-before-definition,unsubscriptable-object,no-value-for-parameter,no-name-in-module,no-method-argument,no-self-argument
import re
from .base import *
from .base import _get_tag_type_name, _is_nbt_tag, _is_nbt_tag_type, _coerce_nbt_tag, _is_end_tag, _raise_end_store_error
try:
    from typing import TypeVar, Self
    Tag = TypeVar("Tag")
except ImportError:
    pass

_KEY_BLACKLIST = frozenset((
    "_uuid",
    "modelName"
))

def _quote_string(value): # type: (str) -> str
    return ("'%s'" % value.replace("'", "\\'")) if '"' in value else '"%s"' % value.replace('"', '\\"')

def _quote_color_string(value): # type: (str) -> str
    return ("'§a%s§r'" % value.replace("'", "\\'")) if '"' in value else '"§a%s§r"' % value.replace('"', '\\"')

def _to_snbt(value):
    to_snbt = getattr(value, "to_snbt", None)
    return to_snbt() if to_snbt else str(value)

def _cut_str(obj): # type: (Base) -> str
    s = obj.colorify()
    return ("%s ... %s" % (s[:40], s[-40:])) if len(s) > 80 else s

try:
    long # type: ignore
except NameError:
    long = int

class End(Base):
    tag_id = 0
    tag_name = "TAG_End"
    suffix = ""
    colorify = lambda self: "TAG_End"
    __eq__ = lambda self, other: True if other is None else Base.__eq__(self, other)

class Byte(BaseInteger):
    tag_id = 1
    tag_name = "TAG_Byte"
    limit = 128
    suffix = "b"

class Short(BaseInteger):
    tag_id = 2
    tag_name = "TAG_Short"
    limit = 32768
    suffix = "s"

class Int(BaseInteger):
    tag_id = 3
    tag_name = "TAG_Int"
    limit = 2 ** 31
    suffix = ""

class Long(Base, long):
    tag_id = 4
    tag_name = "TAG_Long"
    limit = 2 ** 63
    suffix = "l"

    def colorify(self):
        return "§6%s§cl§r" % int(self)

    def __str__(self):
        return "%sl" % int(self)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, int(self))

    def _serialize_value(self):
        return int(self)


class Float(Base, float):
    tag_id = 5
    tag_name = "TAG_Float"
    suffix = "f"

    def colorify(self):
        return "§6%s§cf§r" % float(self)

    def __str__(self):
        return "%sf" % float(self)
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, float(self))

    def _serialize_value(self):
        return float(self)

class Double(Base, float):
    tag_id = 6
    tag_name = "TAG_Double"
    suffix = "d"

    def colorify(self):
        return "§6%s§cd§r" % float(self)
    
    def __str__(self):
        return "%sd" % float(self)
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, float(self))

    def _serialize_value(self):
        return float(self)

class ByteArray(BaseArray):
    tag_id = 7
    tag_name = "TAG_Byte_Array"
    suffix = "B"
    item_type = Byte


class String(Base, str):
    tag_id = 8
    tag_name = "TAG_String"

    def _serialize_value(self):
        return self[:]

    def colorify(self):
        return _quote_color_string(self)

    def to_snbt(self):
        return _quote_string(self)
    
    def __str__(self):
        return self[:]

class List(Base, list):
    __metaclass__ = ListMeta
    tag_id = 9
    tag_name = "TAG_List"
    item_type = None # type: type[Base]

    def __new__(cls, values=None, item_type=None):
        return super(List, cls).__new__(cls)

    @classmethod
    def _resolve_item_type(cls, values, item_type):
        item_type = cls.item_type if item_type is None else item_type
        if item_type is not None:
            if not _is_nbt_tag_type(item_type):
                raise NBTStoreError("列表类型必须为具体NBT标签类,而非 %s" % _get_tag_type_name(item_type))
            return item_type, True
        if not values:
            return None, False
        item_type = type(values[0])
        if not _is_nbt_tag(values[0]):
            raise NBTStoreError("未指定类型的列表元素必须为具体NBT标签实例,而非 %s" % _get_tag_type_name(values[0]))
        for value in values[1:]:
            if type(value) != item_type:
                raise NBTStoreError("列表元素类型不一致,期望 %s, 实际为 %s" % (_get_tag_type_name(item_type), _get_tag_type_name(value)))
        return item_type, False

    def __init__(self, values=None, item_type=None):
        values = [] if values is None else list(values)
        self.item_type, self._specified_item_type = self._resolve_item_type(values, item_type)
        super(List, self).__init__()
        if values:
            super(List, self).extend(self._normalize_values(values))

    def serialize(self):
        return [x.serialize() for x in self]
    
    def __getitem__(self, index):
        return super(List, self).__getitem__(index)
    
    def _normalize_value(self, value):
        if self.item_type is None:
            if _is_nbt_tag(value):
                self.item_type = value.__class__
                return value
            else:
                raise NBTStoreError("未指定类型的列表添加的第一个数据必须为具体NBT标签实例,而非 %s" % _get_tag_type_name(value))
        if type(value) == self.item_type:
            return value
        if not self._specified_item_type:
            raise NBTStoreError("数据类型 %s 与列表类型 %s 不匹配" % (_get_tag_type_name(value), _get_tag_type_name(self.item_type)))
        return _coerce_nbt_tag(self.item_type, value, "列表元素")

    def _normalize_values(self, values):
        result = []
        for value in values:
            result.append(self._normalize_value(value))
        return result

    def append(self, value): # type: (Base) -> None
        super(List, self).append(self._normalize_value(value))
        
    def extend(self, other): # type: (List) -> None
        return super(List, self).extend(self._normalize_values(other))
        
    def insert(self, index, value): # type: (int, Base) -> None
        super(List, self).insert(index, self._normalize_value(value))
    
    def __setitem__(self, index, value):
        if isinstance(index, slice):
            raise NBTStoreError("不支持的切片对象 %s" % index)
        super(List, self).__setitem__(index, self._normalize_value(value))
        
    def __bool__(self):
        return all(self)
    
    def colorify(self):
        return "[%s]" % ", ".join(x.colorify() for x in self)

    def to_snbt(self):
        return "[%s]" % ", ".join(_to_snbt(i) for i in self)

    __str__ = to_snbt
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, super(List, self).__repr__())
        
class Compound(Base, dict): # 还缺点啥,例如update
    tag_id = 10
    tag_name = "TAG_Compound"

    def __init__(self, mapping=None): # type: (dict) -> None
        super(Compound, self).__init__()
        if mapping:
            for k, v in mapping.items():
                self[k] = v

    def serialize(self): # type: () -> dict
        return {k: v.serialize() for k, v in self.items()}

    def path(self, path):  # type: (str) -> Base | None
        """通过NBTPath获取子标签（高性能 + 支持单引号）"""
        tokens = nbtpath_parse(path)

        data = self
        for t, v in tokens:
            if t == _T_KEY:
                if not isinstance(data, Compound):
                    return None
                nxt = data.get(v, end)
                if nxt is end:
                    return None
                data = nxt
            else:
                if not isinstance(data, List):
                    return None
                idx = v
                if idx < 0:
                    idx += len(data)
                if idx < 0 or idx >= len(data):
                    return None
                data = data[idx]
        return data

    def modify(self, path, value):  # type: (str, Base) -> None
        """通过NBTPath修改子标签（高性能 + 支持单引号 + 自动建中间节点）"""
        _raise_end_store_error(value)
        if not _is_nbt_tag(value):
            raise NBTStoreError("值必须为NBT标签对象")

        tokens = nbtpath_parse(path)
        if not tokens:
            raise NBTStoreError("不支持修改根标签: %s" % path)

        data = self
        last = len(tokens) - 1

        _Compound = Compound
        _List = List
        _err = NBTStoreError

        for i, (t, v) in enumerate(tokens):
            is_last = (i == last)

            if t == _T_KEY:
                if not isinstance(data, Compound):
                    raise _err("路径期望Compound，但遇到 %s" % type(data))

                if is_last:
                    data[v] = value
                    return

                nxt_t = tokens[i + 1][0]
                cur = data.get(v, end)

                if cur is end:
                    if nxt_t == _T_KEY:
                        cur = _Compound()
                    else:
                        cur = _List([])
                    data[v] = cur

                data = cur
                continue

            if not isinstance(data, List):
                raise _err("路径期望List，但遇到 %s" % type(data))

            idx = v
            if idx < 0:
                idx += len(data)
            if idx < 0:
                raise _err("无效负索引: %s" % v)

            if is_last:
                if idx < len(data):
                    data[idx] = value
                else:
                    data.insert(idx, value)
                return

            nxt_t = tokens[i + 1][0]
            want = _Compound() if nxt_t == _T_KEY else _List([])

            if idx < len(data):
                cur = data[idx]
                if nxt_t == _T_KEY:
                    if not isinstance(cur, Compound):
                        data[idx] = want
                        cur = want
                else:
                    if not isinstance(cur, List):
                        data[idx] = want
                        cur = want
                data = cur
            else:
                data.insert(idx, want)
                data = want

        raise _err("修改失败: %s" % path)
    
    def colorify(self): # type: () -> str
        result = []
        for k, v in self.items():
            if not k or k[0].isdigit() or re.match(r"[:,\-\{\}\[\]]", k):
                k = ("'§b%s§r'" % k.replace("'", "\\'")) if '"' in k else '"§b%s§r"' % k.replace('"', '\\"')
            else:
                k = "§b%s§r" % k
            result.append("%s: %s§r" % (k, v.colorify()))
        return "{%s}" % ", ".join(result)

    def to_snbt(self):
        result = []
        for k, v in self.items():
            if not k or k[0].isdigit() or re.match(r"[:,\-\{\}\[\]]", k):
                k = ("'%s'" % k.replace("'", "\\'")) if '"' in k else '"%s"' % k.replace('"', '\\"')
            else:
                k = "%s" % k
            result.append("%s: %s" % (k, _to_snbt(v)))
        return "{%s}" % ", ".join(result)

    __str__ = to_snbt

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, super(Compound, self).__repr__())
    
    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise NBTStoreError("键必须为字符串")
        if key in _KEY_BLACKLIST:
            raise NBTStoreError("应规则要求,禁止使用键值: %s" % key)
        _raise_end_store_error(value)
        if not _is_nbt_tag(value):
            raise NBTStoreError("值必须为NBT标签对象")
        super(Compound, self).__setitem__(key, value)

    def get(self, key, default=None): # type: (str, Tag) -> Tag
        if not isinstance(key, str):
            raise NBTStoreError("键必须为字符串")
        if default is not None and not _is_nbt_tag(default) and not _is_end_tag(default):
            raise NBTStoreError("指定默认值必须为NBT标签对象")
        return super(Compound, self).get(key, default)
        

    def setdefault(self, key, default): # type: (str, Tag) -> Tag
        if not isinstance(key, str):
            raise NBTStoreError("键必须为字符串")
        if key in _KEY_BLACKLIST:
            raise NBTStoreError("应规则要求,禁止使用键值: %s" % key)
        _raise_end_store_error(default)
        if not _is_nbt_tag(default):
            raise NBTStoreError("指定默认值必须为NBT标签对象")
        return super(Compound, self).setdefault(key, default)

class IntArray(BaseArray):
    tag_id = 11
    tag_name = "TAG_Int_Array"
    suffix = "I"
    item_type = Int

class LongArray(BaseArray):
    tag_id = 12
    tag_name = "TAG_Long_Array"
    suffix = "L"
    item_type = Long

end = End()
_T_KEY = 1

__all__ = [
    "End", "Byte", "Short", "Int", "Long", "Float", "Double", "ByteArray", "String", "List", "Compound", "IntArray", "LongArray"
]
