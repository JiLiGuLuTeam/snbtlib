# -*- coding: utf-8 -*-
# pylint: disable=undefined-variable,used-before-assignment,too-many-function-args,access-member-before-definition,unsubscriptable-object,no-value-for-parameter,no-name-in-module,no-method-argument,no-self-argument
"""
纯 Python 实现的整数数组 array, 用法与 Python 2.7 标准库 array.array 相同

与标准库的差异:
- 只支持类型码 b (1 字节) 与 i (4 字节), 其余类型码报 ValueError
- 类型码只接受 str
- 没有 buffer_info/tofile/fromfile/read/write/tounicode/fromunicode, 不支持 pickle
- fromstring() 只接受 str
"""
from struct import pack as _pack, unpack as _unpack

_LONG_MIN = -0x8000000000000000
_LONG_MAX = 0x7FFFFFFFFFFFFFFF

def _as_long(v):
    """同 PyArg_Parse 的 l 格式: 拒绝浮点, 其余经 __int__ 取整, 超出 64 位报 OverflowError"""
    if isinstance(v, float):
        raise TypeError("integer argument expected, got float")
    if not isinstance(v, (int, long)):
        int_method = getattr(type(v), "__int__", None)
        if int_method is None:
            raise TypeError("an integer is required")
        v = int_method(v)
        if not isinstance(v, (int, long)):
            raise TypeError("__int__ method should return an integer")
    v = int(v)
    if not _LONG_MIN <= v <= _LONG_MAX:
        raise OverflowError("Python int too large to convert to C long")
    return v

def _to_b(v):
    """同标准库 b 类型: 先按 short 转换, 再检查 signed char 范围"""
    v = _as_long(v)
    if v < -32768:
        raise OverflowError("signed short integer is less than minimum")
    if v > 32767:
        raise OverflowError("signed short integer is greater than maximum")
    if v < -128:
        raise OverflowError("signed char is less than minimum")
    if v > 127:
        raise OverflowError("signed char is greater than maximum")
    return v

def _to_i(v):
    v = _as_long(v)
    if v > 2147483647:
        raise OverflowError("signed integer is greater than maximum")
    if v < -2147483648:
        raise OverflowError("signed integer is less than minimum")
    return v

# 类型码: (itemsize, struct 格式, 元素转换)
_TYPES = {
    "b": (1, "b", _to_b),
    "i": (4, "i", _to_i),
}

def _index(item):
    """同 PyNumber_AsSsize_t(item, IndexError), item 没有 __index__ 时返回 None"""
    index_method = getattr(type(item), "__index__", None)
    if index_method is None:
        return None
    i = index_method(item)
    if not isinstance(i, (int, long)):
        raise TypeError("__index__ returned non-(int,long) (type %s)" % type(i).__name__)
    if not _LONG_MIN <= i <= _LONG_MAX:
        raise IndexError("cannot fit '%s' into an index-sized integer" % type(item).__name__)
    return int(i)

def _plain(typecode, data):
    """切片/拼接/重复/拷贝的结果与标准库相同, 总是基类 array 而不是调用者的子类"""
    obj = object.__new__(array)
    obj._typecode = typecode
    obj._data = data
    return obj

class array(object):
    """整数数组, 元素按类型码的范围存储, 取出的元素是 int"""
    __slots__ = ("_typecode", "_data", "__weakref__")

    def __new__(cls, *args, **kwargs):
        if cls is array and kwargs:
            raise TypeError("array.array() does not take keyword arguments")
        argc = len(args)
        if argc == 0:
            raise TypeError("array() takes at least 1 argument (0 given)")
        if argc > 2:
            raise TypeError("array() takes at most 2 arguments (%d given)" % argc)
        typecode = args[0]
        if not isinstance(typecode, str) or len(typecode) != 1:
            raise TypeError("array() argument 1 or typecode must be char (string or ascii-unicode with length 1), not %s" % type(typecode).__name__)
        initial = args[1] if argc == 2 else None
        it = iter(initial) if argc == 2 and not isinstance(initial, (list, tuple, str)) else None
        if typecode not in _TYPES:
            raise ValueError("bad typecode (must be b or i)")
        self = object.__new__(cls)
        self._typecode = typecode
        if isinstance(initial, (list, tuple)):
            convert = _TYPES[typecode][2]
            self._data = [convert(v) for v in initial]
            return self
        self._data = []
        if isinstance(initial, str):
            array.fromstring(self, initial)
        elif it is not None:
            array.extend(self, it)
        return self

    typecode = property(lambda self: self._typecode, doc="类型码")
    itemsize = property(lambda self: _TYPES[self._typecode][0], doc="每个元素的字节数")

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, v):
        for item in self._data:
            if item == v:
                return True
        return False

    def __getitem__(self, item):
        data = self._data
        i = _index(item)
        if i is not None:
            if i < 0:
                i += len(data)
            if not 0 <= i < len(data):
                raise IndexError("array index out of range")
            return data[i]
        if isinstance(item, slice):
            return _plain(self._typecode, data[item])
        raise TypeError("array indices must be integers")

    def __setitem__(self, item, v):
        data = self._data
        i = _index(item)
        if i is not None:
            if i < 0:
                i += len(data)
            if not 0 <= i < len(data):
                raise IndexError("array assignment index out of range")
            data[i] = _TYPES[self._typecode][2](v)
            return
        if not isinstance(item, slice):
            raise TypeError("array indices must be integer")
        start, stop, step = item.indices(len(data))
        if not isinstance(v, array):
            raise TypeError('can only assign array (not "%s") to array slice' % type(v).__name__)
        if v._typecode != self._typecode:
            raise TypeError("bad argument type for built-in operation")
        values = list(v._data)
        if step != 1:
            # 扩展切片赋空数组时删除对应元素, 这点与 list 不同
            if not values:
                del data[item]
                return
            slice_length = len(xrange(start, stop, step))
            if len(values) != slice_length:
                raise ValueError("attempt to assign array of size %d to extended slice of size %d" % (len(values), slice_length))
        data[item] = values

    def __delitem__(self, item):
        data = self._data
        i = _index(item)
        if i is not None:
            if i < 0:
                i += len(data)
            if not 0 <= i < len(data):
                raise IndexError("array assignment index out of range")
            del data[i]
            return
        if not isinstance(item, slice):
            raise TypeError("array indices must be integer")
        del data[item]

    # a[i:j] 这类简单切片走下面三个方法, 下标越界时收拢到 [0, len]
    def __getslice__(self, i, j):
        data = self._data
        i = min(max(i, 0), len(data))
        j = min(max(j, i), len(data))
        return _plain(self._typecode, data[i:j])

    def __setslice__(self, i, j, v):
        if not isinstance(v, array):
            raise TypeError('can only assign array (not "%s") to array slice' % type(v).__name__)
        if v._typecode != self._typecode:
            raise TypeError("bad argument type for built-in operation")
        data = self._data
        i = min(max(i, 0), len(data))
        j = min(max(j, i), len(data))
        data[i:j] = list(v._data)

    def __delslice__(self, i, j):
        data = self._data
        i = min(max(i, 0), len(data))
        j = min(max(j, i), len(data))
        del data[i:j]

    def __add__(self, other):
        if not isinstance(other, array):
            raise TypeError('can only append array (not "%s") to array' % type(other).__name__)
        if other._typecode != self._typecode:
            raise TypeError("bad argument type for built-in operation")
        return _plain(self._typecode, self._data + other._data)

    def __iadd__(self, other):
        if not isinstance(other, array):
            raise TypeError('can only extend array with array (not "%s")' % type(other).__name__)
        if other._typecode != self._typecode:
            raise TypeError("can only extend with array of same kind")
        self._data.extend(other._data)
        return self

    def __mul__(self, n):
        if getattr(type(n), "__index__", None) is None:
            raise TypeError("can't multiply sequence by non-int of type '%s'" % type(n).__name__)
        return _plain(self._typecode, self._data * n)

    __rmul__ = __mul__

    def __imul__(self, n):
        if getattr(type(n), "__index__", None) is None:
            raise TypeError("can't multiply sequence by non-int of type '%s'" % type(n).__name__)
        self._data *= n
        return self

    # 只和 array 比较, 按元素逐个比, 类型码不同也可以比
    def __eq__(self, other):
        return self._data == other._data if isinstance(other, array) else NotImplemented

    def __ne__(self, other):
        return self._data != other._data if isinstance(other, array) else NotImplemented

    def __lt__(self, other):
        return self._data < other._data if isinstance(other, array) else NotImplemented

    def __le__(self, other):
        return self._data <= other._data if isinstance(other, array) else NotImplemented

    def __gt__(self, other):
        return self._data > other._data if isinstance(other, array) else NotImplemented

    def __ge__(self, other):
        return self._data >= other._data if isinstance(other, array) else NotImplemented

    def __hash__(self):
        # 与标准库相同: array 本身不可哈希, 子类按对象身份哈希
        if type(self) is array:
            raise TypeError("unhashable type: 'array.array'")
        return object.__hash__(self)

    def __repr__(self):
        if not self._data:
            return "array('%s')" % self._typecode
        return "array('%s', %r)" % (self._typecode, self._data)

    def __copy__(self):
        return _plain(self._typecode, list(self._data))

    def __deepcopy__(self, memo):
        return _plain(self._typecode, list(self._data))

    def append(self, v):
        self._data.append(_TYPES[self._typecode][2](v))

    def byteswap(self):
        data = self._data
        fmt = "%d%s" % (len(data), _TYPES[self._typecode][1])
        data[:] = _unpack("<" + fmt, _pack(">" + fmt, *data))

    def count(self, v):
        return self._data.count(v)

    def extend(self, iterable):
        if isinstance(iterable, array):
            if iterable._typecode != self._typecode:
                raise TypeError("can only extend with array of same kind")
            self._data.extend(iterable._data)
            return
        # 逐个追加, 中途转换失败时已追加的元素保留
        convert = _TYPES[self._typecode][2]
        append = self._data.append
        for v in iterable:
            append(convert(v))

    def fromlist(self, lst):
        if not isinstance(lst, list):
            raise TypeError("arg must be list")
        convert = _TYPES[self._typecode][2]
        self._data.extend([convert(v) for v in lst])

    def fromstring(self, s):
        """按本机字节序把字符串解释为机器值追加到末尾"""
        if not isinstance(s, str):
            raise TypeError("fromstring() argument 1 must be string or read-only buffer, not %s" % ("None" if s is None else type(s).__name__))
        itemsize, code = _TYPES[self._typecode][:2]
        if len(s) % itemsize:
            raise ValueError("string length not a multiple of item size")
        self._data.extend(_unpack("=%d%s" % (len(s) // itemsize, code), s))

    def index(self, v):
        for i, item in enumerate(self._data):
            if item == v:
                return i
        raise ValueError("array.index(x): x not in list")

    def insert(self, i, v):
        i = _as_long(i)
        v = _TYPES[self._typecode][2](v)
        # 先收拢到 [0, len] 再交给 list.insert, 不受宿主 Py_ssize_t 位数影响
        data = self._data
        if i < 0:
            i = max(i + len(data), 0)
        data.insert(min(i, len(data)), v)

    def pop(self, i=-1):
        i = _as_long(i)
        data = self._data
        if not data:
            raise IndexError("pop from empty array")
        if i < 0:
            i += len(data)
        if not 0 <= i < len(data):
            raise IndexError("pop index out of range")
        return data.pop(i)

    def remove(self, v):
        data = self._data
        for i, item in enumerate(data):
            if item == v:
                del data[i]
                return
        raise ValueError("array.remove(x): x not in list")

    def reverse(self):
        self._data.reverse()

    def tolist(self):
        return list(self._data)

    def tostring(self):
        """按本机字节序转成机器值字符串"""
        data = self._data
        return _pack("=%d%s" % (len(data), _TYPES[self._typecode][1]), *data)
