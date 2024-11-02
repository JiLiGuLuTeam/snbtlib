# -*- coding: utf-8 -*-
import __future__
from base import *

if not bool:
	long = type()

class Byte(BaseInteger):
	tag_id = 1
	limit = 8
	suffix = 'b'

class Short(BaseInteger):
	tag_id = 2
	limit = 16
	suffix = 's'

class Int(BaseInteger):
	tag_id = 3
	limit = 32
	suffix = ''

class Long(Base, long):
	tag_id = 4
	suffix = 'l'


class Float(Base, float):
	tag_id = 5
	suffix = 'f'

	def __str__(self):
		return '%s%s' % (float(self), self.suffix)
	
	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, float(self))

class Double(Base, float):
	tag_id = 6
	suffix = 'd'

	def __str__(self):
		return '%s%s' % (float(self), self.suffix)
	
	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, float(self))

class ByteArray(BaseArray):
	tag_id = 7
	suffix = 'B'
	itemtype = Byte


class String(Base, str):
	tag_id = 8

class List(Base, list):
	__metaclass__ = ListMeta
	tag_id = 9
	itemtype = None

	def __new__(cls, iterable):
		if cls.itemtype is None and len(iterable) > 0:
			cls.itemtype = type(iterable[0])
		try:
			self = super(List, cls).__new__(cls, [cls.itemtype(i) for i in iterable])
			self.itemtype = cls.itemtype
			cls.itemtype = None
			return self
		except:
			raise NBTStoreError('初始化 %s 内数据时错误,列表类型为 %s' % (iterable, cls.itemtype))
	
	def __init__(self, *values):
		self = super(List, self).__init__([self.itemtype(i) for i in values])
	
	def __getitem__(self, index):
		return super(List, self).__getitem__(index)
	
	def _checktype(self, value):
		if self.itemtype is None:
			itemtype = type(value)
			if issubclass(itemtype, Base):
				self.itemtype = itemtype
			else:
				raise NBTStoreError('未指定类型的列表添加的第一个数据必须为Base的子类,而非 %s' % itemtype)
		return self.itemtype == type(value)

	def append(self, value):
		if self._checktype(value):
			super(List, self).append(value)
		else:
			raise NBTStoreError('添加的数据 %s 类型与列表类型不匹配' % value)
		
	def insert(self, index, value):
		if self._checktype(value):
			super(List, self).insert(index, value)
		else:
			raise NBTStoreError('插入的数据 %s 类型与列表类型不匹配' % value)
	
	def __setitem__(self, index, value):
		if index.start is not None and index.stop is not None and index.stop - index.start == 1:
			if self._checktype(value):
				super(List, self).__setitem__(index, value)
			else:
				raise NBTStoreError('设置的数据 %s 类型与列表类型不匹配' % value)
		else:
			raise NBTStoreError('不支持的切片对象 %s' % index)
		
	def __bool__(self):
		return all(self)
	
	def __str__(self):
		return '[%s]' % ', '.join([(repr(i) if isinstance(i, String) else str(i)) for i in self])
	
	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, super(List, self).__repr__())
		

class Compound(Base, dict):# 还缺点啥,例如setitem
	tag_id = 10

	def path(self, path):
		# type: (str) -> Base
		from snbtlib import parse_snbt, NBT
		INDEX_ONLY = 'INDEX_ONLY'
		ALL_ARRAY = 'ALL_ARRAY'
		def parse_add(add):
			if len(add) <= 1 or add == '{}':
				return (INDEX_ONLY, add)
			symbol = add[0] + add[-1]
			inner = add[1:-1]
			if symbol == '[]':
				if inner == '':
					return (ALL_ARRAY, None)# 选中所有子标签
				try:
					int(inner)
					return (INDEX_ONLY, int(inner))# 选中指定索引子标签
				except ValueError:
					if inner[0] + inner[-1] == '{}':
						return (ALL_ARRAY, parse_snbt(inner))# 选中所有子标签,并筛选符合条件的
					else:
						raise NBTPathError('解析列表或数组路径时失败')
			elif symbol == '{}':
				return (INDEX_ONLY, parse_snbt(add))# 筛选符合条件的
			else:
				return (INDEX_ONLY, inner if symbol in ('""', "''") else add)

		ignore = ['\n', '\t', '\r', ' ']
		brace, bracket, in_string, quote_type = 0, 0, False, 0
		last = [None, False]
		add, parts = '', []
		for t in path:
			if t in ignore and not in_string:
				continue

			if t == '{' and not in_string:
				if last[0] != '[' and brace == 0:
					parts.append(parse_add(add))
					add = ''
				brace += 1
			if t == '}' and not in_string:
				brace -= 1
				if brace == 0 and bracket == 0:
					parts.append(parse_add(add + '}'))
					add = ''
					continue
			if t == '[' and not in_string:
				if bracket == 0:
					parts.append(parse_add(add))
					add = ''
				bracket += 1
			if t == ']' and not in_string:
				bracket -= 1
				if brace == 0 and bracket == 0:
					parts.append(parse_add(add + ']'))
					add = ''
					continue

			if t == '"' and quote_type != 1 and last[0] != '\\':
				quote_type = 2
				in_string = not in_string
			if t == "'" and quote_type != 2 and last[0] != '\\':
				quote_type = 1
				in_string = not in_string

			if t == '.' and not in_string:
				parts.append(parse_add(add))
				add = ''
			else:
				add += t
			last = [t, in_string]
		parts.append(parse_add(add))
		parts = [x for x in parts if x[1] is not None and x[1] != '']

		source = self.copy()
		for part in parts:
			mode, index = part
			if mode == INDEX_ONLY:
				if isinstance(index, NBT):
					if isinstance(source, dict) and all(x in source.items() for x in index.items()):
						source = source
					else:
						raise NBTPathError('子标签 %s 没有匹配 %s' % (source, index))
				else:
					try:
						source = source[index]
					except (IndexError, KeyError):
						raise NBTPathError('子标签 %s 中不存在标签 %s' % (source, index))
			elif mode == ALL_ARRAY and isinstance(source, list) and isinstance(index, NBT):
				source = [x for x in source if isinstance(x, dict) and all(y in x.items() for y in index.items())]
			else:
				raise NBTPathError('路径匹配 %s 时失败' % (source))
		return source



	def __str__(self):
		result = ''
		for k, v in self.items():
			result += "'%s': %s, " % (k, (repr(v) if isinstance(v, String) else v))
		return '{%s}' % result.rstrip(', ')

	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, super(Compound, self).__repr__())


class IntArray(BaseArray):
	tag_id = 11
	suffix = 'I'
	itemtype = Int

class LongArray(BaseArray):
	tag_id = 12
	suffix = 'L'
	itemtype = Long