# -*- coding: utf-8 -*-
import __future__
from array import array
if not isinstance({}.keys(), list):
	xrange = range

class BaseNBTError(Exception):
	def __init__(self, msg):
		self.msg = msg
		super(BaseNBTError, self).__init__(msg)

	translate = ''
	'''错误对应翻译'''

class NBTStoreError(BaseNBTError):
	translate = 'NBT存储错误'

class NBTParseError(BaseNBTError):
	translate = 'NBT解析错误'

class ItemFormatParseError(NBTParseError):
	translate = '物品共通标签解析错误'

class NBTPathError(BaseNBTError):
	translate = 'NBT路径错误'

class Base(object):
	tag_id = 0
	'''当前类型对应ID,同UserData'''
	suffix = ''
	'''当前类型对应后缀,同SNBT'''

class BaseInteger(Base, int):
	limit = 0
	'''当前数字最大范围,为 [-2 ** limit, 2 ** limit)'''

	def __new__(cls, value=0):
		self = super(BaseInteger, cls).__new__(cls, value)
		nrange = 2 ** cls.limit
		if not -nrange < int(self) < nrange:
			raise NBTStoreError('整数 %s 超出该类型给定值范围' % value)
		return self

	def __str__(self):
		return '%s%s' % (int(self), self.suffix)
	
	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, int(self))

class BaseArray(Base, array):
	itemtype = None # type: BaseInteger
	'''当前数组类型'''
	__types = {
		7: 'b',
		11: 'i',
		12: 'l'
	}
	def __new__(cls, iterable):
		self = super(BaseArray, cls).__new__(cls, cls.__types[cls.tag_id], [int(i) for i in iterable])
		return self

	def _checktype(self, value):
		return self.itemtype == type(value)
	
	def __getitem__(self, index):
		return self.itemtype(super(BaseArray, self).__getitem__(index))

	def append(self, value):
		if self._checktype(value):
			super(BaseArray, self).append(int(value))
		else:
			raise NBTStoreError('添加的数据 %s 类型与数组类型不匹配' % value)
		
	def insert(self, index, value):
		if self._checktype(value):
			super(BaseArray, self).insert(index, int(value))
		else:
			raise NBTStoreError('插入的数据 %s 类型与数组类型不匹配' % value)
	
	def __setitem__(self, index, value):
		if index.start is not None and index.stop is not None and index.stop - index.start == 1:
			if self._checktype(value):
				super(BaseArray, self).__setitem__(index, int(value))
			else:
				raise NBTStoreError('设置的数据 %s 类型与数组类型不匹配' % value)
		else:
			raise NBTStoreError('不支持的切片对象 %s' % index)
		
	def __bool__(self):
		return all(self)
	
	def __str__(self):
		result = ''
		for i in self:
			result += '%s%s, ' % (int(i), self.suffix)
		return '[%s; %s]' % (self.suffix, result.strip(', '))
	
	def __repr__(self):
		return '%s([%s])' % (self.__class__.__name__, ', '.join(map(str, self)))

class ListMeta(type):
	try: from tag import List
	except: pass
	def __getitem__(cls, itemtype): # type: (Base) -> List
		'''指定列表类型'''
		cls.itemtype = itemtype
		return cls