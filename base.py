# -*- coding: utf-8 -*-
# pylint: disable=undefined-variable,used-before-assignment,too-many-function-args,access-member-before-definition,unsubscriptable-object,no-value-for-parameter,no-name-in-module,no-method-argument,no-self-argument
from collections import OrderedDict
from array import array
if not isinstance({}.keys(), list):
    xrange = range

class BaseNBTError(Exception):
    TRANSLATION = ""
    """错误对应翻译"""

class NBTStoreError(BaseNBTError):
    TRANSLATION = "NBT存储错误"

class NBTParseError(BaseNBTError):
    TRANSLATION = "NBT解析错误"
    def __init__(self, snbt, index, msg):
        self.snbt = snbt
        self.index = max(0, min(index, len(snbt)))
        self.msg = msg
        line_start = snbt.rfind("\n", 0, self.index)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1
        self.line = snbt.count("\n", 0, self.index) + 1
        self.column = self.index - line_start + 1
        line_prefix = snbt[line_start:self.index].expandtabs(4).replace("\r", "")
        if len(line_prefix) > 26:
            line_prefix = "..." + line_prefix[-23:]
        BaseNBTError.__init__(
            self,
            "%s 位置: 第 %s 行, 第 %s 列, 索引 %s\n%s" % (
                (line_prefix + " <-") if line_prefix else "<-",
                self.line,
                self.column,
                self.index,
                msg
            )
        )

class ItemFormatParseError(BaseNBTError):
    TRANSLATION = "物品共通标签解析错误"

class NBTPathError(NBTParseError):
    TRANSLATION = "NBT路径错误"

class Base(object):
    tag_id = 0
    """当前类型对应ID,同userData"""
    suffix = ""
    """当前类型对应后缀,同SNBT"""

    def serialize(self):
        """返回自身数据转换为userData的格式"""
        _raise_end_store_error(self)
        if not _is_nbt_tag(self):
            raise NBTStoreError("%s 为抽象NBT标签,不能直接存储" % _get_tag_type_name(self))
        return {"__type__": self.tag_id, "__value__": self._serialize_value()}

    def _serialize_value(self):
        return self
    
    def colorify(self): # type: () -> str
        """返回附有样式代码的SNBT"""
        return ""

    def to_snbt(self): # type: () -> str
        return str(self)

def _get_tag_type_name(value):
    cls = value if isinstance(value, type) else value.__class__
    if getattr(cls, "tag_name", None):
        return cls.tag_name
    return cls.__name__

_VALID_TAG_IDS = frozenset(xrange(1, 13))

def _is_end_tag(value):
    return isinstance(value, Base) and value.__class__.tag_id == 0

def _is_nbt_tag_type(tag_type):
    return isinstance(tag_type, type) and issubclass(tag_type, Base) and tag_type.tag_id in _VALID_TAG_IDS

def _is_nbt_tag(value):
    return isinstance(value, Base) and _is_nbt_tag_type(value.__class__)

def _raise_end_store_error(value):
    if _is_end_tag(value):
        raise NBTStoreError("TAG_End 类型不可存储")

def _coerce_nbt_tag(tag_type, value, value_desc="值"):
    if not _is_nbt_tag_type(tag_type):
        raise NBTStoreError("%s类型必须为具体NBT标签类,而非 %s" % (value_desc, _get_tag_type_name(tag_type)))
    _raise_end_store_error(value)
    if _is_nbt_tag(value) and isinstance(value, tag_type):
        return value
    try:
        return tag_type(value)
    except BaseNBTError:
        raise
    except Exception:
        raise NBTStoreError("%s %s 无法转换为 %s" % (value_desc, value, _get_tag_type_name(tag_type)))

class BaseInteger(Base, int):
    limit = 0
    """当前数字最大范围,为 [-limit, limit)"""

    def __new__(cls, value=0):
        self = super(BaseInteger, cls).__new__(cls, value)
        if not -cls.limit <= int(self) < cls.limit:
            raise NBTStoreError("整数 %s 超出该类型给定值范围" % value)
        return self
    
    def colorify(self):
        return "§6%s§c%s§r" % (int(self), self.suffix)

    def __str__(self):
        return "%s%s" % (int(self), self.suffix)
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, int(self))

    def _serialize_value(self):
        return int(self)

_types = {
    7: "b",
    11: "i",
    12: "l"
}
class BaseArray(Base, array):
    item_type = None # type: type[BaseInteger]
    """当前数组类型"""
    def __new__(cls, iterable=()):
        if not _is_nbt_tag_type(cls.item_type):
            raise NBTStoreError("%s 的数组元素类型未定义" % _get_tag_type_name(cls))
        values = [int(_coerce_nbt_tag(cls.item_type, value, "数组元素")) for value in iterable]
        return super(BaseArray, cls).__new__(cls, _types[cls.tag_id], values)

    def _serialize_value(self):
        return [int(i) for i in self]

    def _normalize_value(self, value):
        return _coerce_nbt_tag(self.item_type, value, "数组元素")

    def __getitem__(self, index):
        result = super(BaseArray, self).__getitem__(index)
        if isinstance(index, slice):
            return [self.item_type(value) for value in result]
        return self.item_type(result)

    def append(self, value): # type: (Base) -> None
        super(BaseArray, self).append(int(self._normalize_value(value)))
        
    def insert(self, index, value): # type: (int, Base) -> None
        super(BaseArray, self).insert(index, int(self._normalize_value(value)))
    
    def __setitem__(self, index, value):
        if isinstance(index, slice):
            raise NBTStoreError("不支持的切片对象 %s" % index)
        super(BaseArray, self).__setitem__(index, int(self._normalize_value(value)))
        
    def __bool__(self):
        return all(self)
    
    def colorify(self):
        result = ""
        for i in self:
            result += "§6%s§c%s§r, " % (int(i), self.suffix)
        return "[§c%s§r; %s]" % (self.suffix, result.strip(", "))
    
    def __str__(self):
        result = ""
        for i in self:
            result += "%s%s, " % (int(i), self.suffix)
        return "[%s; %s]" % (self.suffix, result.strip(", "))
    
    def __repr__(self):
        return "%s([%s])" % (self.__class__.__name__, ", ".join(map(str, self)))

class ListMeta(type):
    _typed_factories = {}

    def __getitem__(cls, itemtype): # type: (Base) -> ...
        """指定列表类型"""
        if not _is_nbt_tag_type(itemtype):
            raise NBTStoreError("列表类型必须为具体NBT标签类,而非 %s" % _get_tag_type_name(itemtype))
        key = (cls, itemtype)
        factory = cls._typed_factories.get(key)
        if factory is None:
            factory = _TypedListFactory(cls, itemtype)
            cls._typed_factories[key] = factory
        return factory

class _TypedListFactory(object):
    __slots__ = ("_list_type", "_item_type")

    def __init__(self, list_type, item_type):
        self._list_type = list_type
        self._item_type = item_type

    def __call__(self, values=None):
        return self._list_type(values, self._item_type)

    def __repr__(self):
        return "%s[%s]" % (self._list_type.__name__, _get_tag_type_name(self._item_type))

    __str__ = __repr__
    
# token types (use small ints for speed)
_T_KEY = 1
_T_IDX = 2

paths_cache = OrderedDict()
def nbtpath_parse(path):
    if path is None:
        return []
    if path in paths_cache:
        if len(paths_cache) > 2000:
            paths_cache.popitem(last=False)
        return paths_cache[path]

    s = path
    n = len(s)
    i = 0
    out = []

    # local bindings for speed
    append = out.append
    _ord = ord

    def _is_ws(ch):
        o = _ord(ch)
        return o == 32 or o == 9 or o == 10 or o == 13

    def _skip_ws(j): # type: (int) -> int
        while j < n and _is_ws(s[j]):
            j += 1
        return j

    def _read_quoted(j):
        q = s[j]
        j += 1
        buf = []
        bappend = buf.append
        while j < n:
            c = s[j]
            if c == '\\':
                j += 1
                if j >= n:
                    raise NBTPathError(path, j, "转义符后缺少字符")
                esc = s[j]
                # handle a few common escapes; otherwise literal
                if esc == 'n':
                    bappend('\n')
                elif esc == 't':
                    bappend('\t')
                elif esc == 'r':
                    bappend('\r')
                else:
                    bappend(esc)
                j += 1
                continue
            if c == q:
                j += 1
                return ''.join(buf), j
            bappend(c)
            j += 1
        raise NBTPathError(path, j, "引号未闭合")

    def _skip_braces(j):
        # s[j] == '{'
        depth = 0
        while j < n:
            c = s[j]
            if c == '{':
                depth += 1
                j += 1
                continue
            if c == '}':
                depth -= 1
                j += 1
                if depth == 0:
                    return j
                continue
            if c == '"' or c == "'":
                _, j = _read_quoted(j)
                continue
            if c == '\\':
                j += 2
                continue
            j += 1
        raise NBTPathError(path, j, "大括号未闭合")

    i = _skip_ws(i)

    # allow leading "{}" root selector (skip)
    if i + 1 < n and s[i] == '{' and s[i + 1] == '}':
        i += 2
        i = _skip_ws(i)
        if i >= n:
            return []

    while i < n:
        i = _skip_ws(i)
        if i >= n:
            break

        c = s[i]

        # separator
        if c == '.':
            i += 1
            continue

        # filter/root braces after key: foo{} / foo{...}
        if c == '{':
            i = _skip_braces(i)
            continue

        # list index
        if c == '[':
            start = i
            i += 1
            i = _skip_ws(i)
            if i >= n:
                raise NBTPathError(path, start, "方括号未闭合")

            # read until ']'
            j = i
            while j < n and s[j] != ']':
                j += 1
            if j >= n:
                raise NBTPathError(path, start, "方括号未闭合")

            inside = s[i:j].strip()
            i = j + 1

            if inside == "":
                raise NBTPathError(path, start, "不支持 [] 选择器 (批量选择)")

            # only integer index
            try:
                idx = int(inside, 10)
            except Exception:
                raise NBTPathError(path, start, "不支持的索引 [%s] (仅支持整数)" % inside)

            append((_T_IDX, idx))
            continue

        # quoted key
        if c == '"' or c == "'":
            key, i = _read_quoted(i)
            append((_T_KEY, key))
            continue

        # bare key: read until '.', '[', '{', whitespace
        start = i
        j = i
        while j < n:
            cj = s[j]
            if cj == '.' or cj == '[' or cj == '{' or _is_ws(cj):
                break
            j += 1
        if j == start:
            raise NBTPathError(path, i, "无法解析路径字符: %r" % s[i])
        key = s[start:j]
        append((_T_KEY, key))
        i = j

    paths_cache[path] = out
    return out
