# -*- coding: utf-8 -*-
# pylint: disable=undefined-variable,used-before-assignment,too-many-function-args,access-member-before-definition,unsubscriptable-object,no-value-for-parameter,no-name-in-module,no-method-argument,no-self-argument
from . import tag, base
from collections import OrderedDict as _OrderedDict
import re

_FLOAT_PATTERN = re.compile(r"^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?[fF]$")
_DOUBLE_PATTERN = re.compile(r"^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?[dD]$")
_DOUBLE_PATTERN_NOSUFFIX = re.compile(r"^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$")
_BYTE_PATTERN = re.compile(r"^[-+]?[0-9]+[bB]$")
_SHORT_PATTERN = re.compile(r"^[-+]?[0-9]+[sS]$")
_INT_PATTERN = re.compile(r"^[-+]?[0-9]+$")
_LONG_PATTERN = re.compile(r"^[-+]?[0-9]+[lL]$")

_ARRAY_TYPES = {
    "B": (tag.ByteArray, tag.Byte),
    "I": (tag.IntArray, tag.Int),
    "L": (tag.LongArray, tag.Long)
}

def _is_allowed_unquoted_char(ch):
    if "0" <= ch <= "9" or "A" <= ch <= "Z" or "a" <= ch <= "z":
        return True
    return ch in "._+-"

def _tag_name(value):
    return base._get_tag_type_name(value)

def _parse_primitive(token):
    lower_token = token.lower()
    try:
        if _FLOAT_PATTERN.match(token):
            return tag.Float(float(token[:-1]))
        if _BYTE_PATTERN.match(token):
            value = int(token[:-1])
            return tag.Byte(value) if -128 <= value < 128 else tag.String(token)
        if _SHORT_PATTERN.match(token):
            value = int(token[:-1])
            return tag.Short(value) if -32768 <= value < 32768 else tag.String(token)
        if _INT_PATTERN.match(token):
            value = int(token)
            return tag.Int(value) if -(2 ** 31) <= value < 2 ** 31 else tag.String(token)
        if _LONG_PATTERN.match(token):
            value = int(token[:-1])
            return tag.Long(value) if -(2 ** 63) <= value < 2 ** 63 else tag.String(token)
        if _DOUBLE_PATTERN.match(token):
            return tag.Double(float(token[:-1]))
        if _DOUBLE_PATTERN_NOSUFFIX.match(token):
            return tag.Double(float(token))
        if lower_token == "true":
            return tag.Byte(1)
        if lower_token == "false":
            return tag.Byte(0)
    except Exception:
        return tag.String(token)
    return tag.String(token)

class _SnbtParser(object):
    __slots__ = ("snbt", "length", "cursor")

    def __init__(self, snbt):
        self.snbt = snbt
        self.length = len(snbt)
        self.cursor = 0

    def parse_root_value(self):
        value = self._read_value()
        self._skip_whitespace()
        if self._can_read():
            self._raise(self.cursor, "SNBT 末尾存在多余内容")
        return value

    def parse_root_compound(self):
        value = self.parse_root_value()
        if not isinstance(value, tag.Compound):
            self._raise(0, "根标签必须是复合标签")
        return value

    def _can_read(self, offset=0):
        return self.cursor + offset < self.length

    def _peek(self, offset=0):
        return self.snbt[self.cursor + offset]

    def _read_char(self):
        ch = self.snbt[self.cursor]
        self.cursor += 1
        return ch

    def _skip_whitespace(self):
        snbt = self.snbt
        cursor = self.cursor
        while cursor < self.length and snbt[cursor].isspace():
            cursor += 1
        self.cursor = cursor

    def _raise(self, index, msg):
        raise base.NBTParseError(self.snbt, index, msg)

    def _expect(self, expected, msg):
        self._skip_whitespace()
        if not self._can_read() or self._peek() != expected:
            self._raise(self.cursor, msg)
        self.cursor += 1

    def _has_element_separator(self):
        self._skip_whitespace()
        if self._can_read() and self._peek() == ",":
            self.cursor += 1
            self._skip_whitespace()
            return True
        return False

    def _read_unquoted_string(self):
        start = self.cursor
        while self._can_read() and _is_allowed_unquoted_char(self._peek()):
            self.cursor += 1
        return self.snbt[start:self.cursor]

    def _read_string_token(self):
        self._skip_whitespace()
        if not self._can_read():
            return ""
        if self._peek() in ("'", '"'):
            return self._read_quoted_string()
        return self._read_unquoted_string()

    def _read_quoted_string(self):
        quote = self._read_char()
        result = []
        while self._can_read():
            current = self._read_char()
            if current == quote:
                return "".join(result)
            if current != "\\":
                result.append(current)
                continue
            if not self._can_read():
                self._raise(self.cursor - 1, "字符串未闭合")
            escaped = self._read_char()
            if escaped == quote or escaped == "\\":
                result.append(escaped)
            else:
                self._raise(self.cursor - 1, "无效的转义字符 '\\%s'" % escaped)
        self._raise(self.cursor, "字符串未闭合")

    def _read_key(self):
        key = self._read_string_token()
        if not key:
            self._raise(self.cursor, "缺少键名")
        return key

    def _read_typed_value(self):
        token_start = self.cursor
        token = self._read_string_token()
        if not token:
            self._raise(token_start, "缺少值")
        return _parse_primitive(token)

    def _set_compound_value(self, compound, key, value, key_start):
        try:
            compound[key] = value
        except base.BaseNBTError as exc:
            self._raise(key_start, str(exc))

    def _read_compound(self):
        compound = tag.Compound()
        self.cursor += 1
        self._skip_whitespace()
        if not self._can_read():
            self._raise(self.cursor, "缺少键名")
        if self._peek() == "}":
            self.cursor += 1
            return compound

        while True:
            key_start = self.cursor
            key = self._read_key()
            self._expect(":", "键名后缺少 ':'")
            value = self._read_value()
            self._set_compound_value(compound, key, value, key_start)

            if not self._has_element_separator():
                break
            if self._can_read() and self._peek() == "}":
                self.cursor += 1
                return compound
        self._expect("}", "复合标签缺少结束符 '}'")
        return compound

    def _build_list(self, values, item_start_positions):
        if not values:
            return tag.List([])

        first_type = type(values[0])
        for index in xrange(1, len(values)):
            if type(values[index]) != first_type:
                self._raise(
                    item_start_positions[index],
                    "列表元素类型不一致, 期望 %s, 实际为 %s" % (_tag_name(values[0]), _tag_name(values[index]))
                )
        return tag.List(values)

    def _read_list(self):
        values = []
        item_start_positions = []
        self.cursor += 1
        self._skip_whitespace()
        if not self._can_read():
            self._raise(self.cursor, "缺少值")
        if self._peek() == "]":
            self.cursor += 1
            return tag.List([])

        while True:
            item_start_positions.append(self.cursor)
            values.append(self._read_value())
            if not self._has_element_separator():
                break
            if self._can_read() and self._peek() == "]":
                self.cursor += 1
                return self._build_list(values, item_start_positions)
            if not self._can_read():
                self._raise(self.cursor, "缺少值")
        self._expect("]", "列表缺少结束符 ']'")
        return self._build_list(values, item_start_positions)

    def _read_array(self):
        values = []
        array_start = self.cursor
        self.cursor += 1
        element_prefix = self._read_char()
        self.cursor += 1

        array_info = _ARRAY_TYPES.get(element_prefix)
        if array_info is None:
            self._raise(array_start + 1, "无效的数组前缀 '%s'" % element_prefix)

        array_cls, item_cls = array_info
        self._skip_whitespace()
        if not self._can_read():
            self._raise(self.cursor, "缺少值")
        if self._peek() == "]":
            self.cursor += 1
            return array_cls(values)

        while True:
            item_start = self.cursor
            value = self._read_value()
            if type(value) is not item_cls:
                self._raise(item_start, "数组 [%s;] 只允许 %s, 实际为 %s" % (element_prefix, item_cls.tag_name, _tag_name(value)))
            values.append(value)
            if not self._has_element_separator():
                break
            if self._can_read() and self._peek() == "]":
                self.cursor += 1
                return array_cls(values)
            if not self._can_read():
                self._raise(self.cursor, "缺少值")
        self._expect("]", "数组缺少结束符 ']'")
        return array_cls(values)

    def _read_list_or_array(self):
        if self._can_read(2) and self._peek(1) not in ("'", '"') and self._peek(2) == ";":
            return self._read_array()
        return self._read_list()

    def _read_value(self):
        self._skip_whitespace()
        if not self._can_read():
            self._raise(self.cursor, "缺少值")

        current = self._peek()
        if current == "{":
            return self._read_compound()
        if current == "[":
            return self._read_list_or_array()
        if current in ("'", '"'):
            return tag.String(self._read_quoted_string())
        return self._read_typed_value()

def parse_value(value_part): # type: (str) -> base.Base
    """按 Minecraft Java 1.18.2 规则解析一个 SNBT 值。"""
    value_part = value_part.strip()
    if not value_part:
        raise base.NBTParseError(value_part, 0, "缺少NBT值")
    return _SnbtParser(value_part).parse_root_value()

_parse_snbt_cache = {} # type: _OrderedDict[str, tag.Compound]
def parse_snbt(snbt): # type: (str) -> tag.Compound
    """将字符串形式的NBT解析为复合标签"""
    snbt = snbt.strip()
    if not snbt:
        return tag.Compound()
    if snbt in _parse_snbt_cache:
        return _parse_snbt_cache[snbt]
    _parse_snbt_cache[snbt] = result = _SnbtParser(snbt).parse_root_compound()
    if len(_parse_snbt_cache) > 1000:
        _parse_snbt_cache.popitem(last=False)
    return result
    
def parse_item_format(value): # type: (str | tag.Compound) -> dict
    """将字符串形式的物品共通标签解析为复合标签"""
    if isinstance(value, str):
        value = parse_snbt(value)
        if "Name" not in value.keys():
            raise base.ItemFormatParseError("物品共通标签缺少标签: Name")
        if "Count" not in value.keys():
            raise base.ItemFormatParseError("物品共通标签缺少标签: Count")
    cache = value.copy()
    id_ = cache.get("Name", "")
    return {
            "newItemName": ("minecraft:%s" % id_) if ":" not in id_ else id_,
            "count": int(cache.get("Count", 0)),
            "newAuxValue": int(cache.get("Damage", 0)),
            "userData": tag.Compound(cache.get("tag", {})).serialize()
        }

def parse_itemDict(value): # type: (dict) -> tag.Compound
    """将 wy itemDict 转换为复合标签"""
    cache = value.copy()
    return tag.Compound({
        "Name": tag.String(cache["newItemName"]),
        "Count": tag.Byte(cache["count"]),
        "Damage": tag.Short(cache["newAuxValue"]),
        "tag": tag.Compound(deserialize_nbt_dict(cache.get("userData") or {}))
    })

_value_types = {
    1: tag.Byte,
    2: tag.Short,
    3: tag.Int,
    4: tag.Long,
    5: tag.Float,
    6: tag.Double,
    8: tag.String
}
_arr_types = {
    7: tag.ByteArray,
    11: tag.IntArray,
    12: tag.LongArray
}
_all_types = {
    9: tag.List,
    10: tag.Compound
}
_all_types.update(_value_types)
_all_types.update(_arr_types)

def _is_typed_payload(value):
    return isinstance(value, dict) and len(value) == 2 and "__type__" in value and "__value__" in value

def _de_parse_value(value):
        return _value_types[value["__type__"]](value["__value__"])

def _de_parse_list(value):
    if isinstance(value, list):
        if len(value) == 0:
            return tag.List([])
        if _is_typed_payload(value[0]):
            return tag.List([_de_parse_list(x) if x["__type__"] in _arr_types else _de_parse_value(x) for x in value])
        if isinstance(value[0], list):
            return tag.List([_de_parse_list(x) for x in value])
        if isinstance(value[0], dict):
            return tag.List([_de_parse_dict(x) for x in value])
        return tag.List(value)
    else:
        return _arr_types[value["__type__"]](value["__value__"])
    
def _de_parse_dict(value):
    result = {}
    for k, v in value.items():
        k = str(k)
        if _is_typed_payload(v):
            result[k] = _de_parse_list(v) if v["__type__"] in {7, 11, 12} else _de_parse_value(v)
        elif isinstance(v, list):
            result[k] = _de_parse_list(v)
        elif isinstance(v, dict):
            result[k] = _de_parse_dict(v)
    return tag.Compound(result)

def deserialize_nbt_dict(user_data): # type: (dict) -> tag.Compound
    """将wy提供的NBT字典(userData)解析为复合标签"""
    return tag.Compound(_de_parse_dict(user_data))

_enchantment_ids = {
    "protection": 0,
    "fire_protection": 1,
    "feather_falling": 2,
    "blast_protection": 3,
    "projectile_protection": 4,
    "thorns": 5,
    "respiration": 6,
    "depth_strider": 7,
    "aqua_affinity": 8,
    "sharpness": 9,
    "smite": 10,
    "bane_of_arthropods": 11,
    "knockback": 12,
    "fire_aspect": 13,
    "looting": 14,
    "efficiency": 15,
    "silk_touch": 16,
    "unbreaking": 17,
    "fortune": 18,
    "power": 19,
    "punch": 20,
    "flame": 21,
    "infinity": 22,
    "luck_of_the_sea": 23,
    "lure": 24,
    "frost_walker": 25,
    "mending": 26,
    "binding_curse": 27,
    "vanishing_curse": 28,
    "impaling": 29,
    "riptide": 30,
    "loyalty": 31,
    "channeling": 32,
    "multishot": 33,
    "piercing": 34,
    "quick_charge": 35,
    "soul_speed": 36,
    "swift_sneak": 37
}

__all__ = ["parse_snbt", "parse_item_format", "parse_itemDict", "deserialize_nbt_dict"]
