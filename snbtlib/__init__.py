# -*- coding: utf-8 -*-
from __future__ import print_function
from traceback import format_exc as _format_exc
from json import loads as _loads
import tag
from base import BaseNBTError, NBTParseError, NBTStoreError, ItemFormatParseError

def _raise(e, key):
    if key == '': key = '.'
    raise e if isinstance(e, NBTParseError) else NBTParseError(('%s: %s, 出现在 %s ' % (e.translate, e.args[0], key)) if isinstance(e, BaseNBTError) else '脚本层错误: 出现在 %s\n%s' % (key, _format_exc()))

def _check_int_valid(obj):
    _type, v = obj['__type__'], obj['__value__']
    vtype = _value_types[_type]
    if 0 < _type < 5 and not (-vtype.limit <= v < vtype.limit):
        raise NBTStoreError('整数 %s 超出该类型给定值范围' % v)

_strs = (str, type(u''))
if not bool:
    long = type()

class NBT(tag.Compound):
    def stringify(self, highlight=False): # type: (bool) -> str
        h = (lambda color, value: ('§%s%s§f' % (color, value))) if highlight else (lambda color, value: value)
        '''返回SNBT'''
        def parse_data(value, upper=False):
            if isinstance(value, int):
                suffix = value.suffix
                return '%s%s' % (h(6, int(value)), h('c', suffix.upper() if upper else suffix))
            elif isinstance(value, float):
                return '%s%s' % (h(6, float(value)), h('c', value.suffix))
            else:
                if '"' in value:
                    return "'%s'" % h('a', repr(str(value))[1:-1])
                return '"%s"' % h('a', value)

        def parse_array(value):
            is_list = isinstance(value, tag.List)
            if is_list:
                result = ''
            else:
                result = '%s; ' % h('c', value.itemtype.__name__[0])
            for v in value:
                if isinstance(v, (int, float, _strs)):
                    result += parse_data(v, not is_list)
                elif isinstance(v, list):
                    result += parse_array(v)
                elif isinstance(v, dict):
                    result += '{%s}' % parse_compound(v)
                result += ', '
            return '[%s]' % result[:-2]
        
        def parse_compound(value):
            result = ''
            for k, v in value.items():
                try:
                    float(k)
                    k = '"%s"' % k
                except ValueError:
                    pass
                if ':' in k:
                    k = '"%s"' % k
                result += '%s: ' % h('b', k)
                if isinstance(v, (int, float, _strs)):
                    result += parse_data(v)
                elif isinstance(v, list):
                    result += parse_array(v)
                elif isinstance(v, dict):
                    result += '{%s}' % parse_compound(v)
                result += ', '
            return '%s' % result[:-2]
        
        return '{%s}' % parse_compound(self)

    def parse(self): # type: () -> UserData
        '''返回当前NBT的UserData对象'''
        return UserData(tag.Compound.parse(self))

    def __str__(self):
        return self.stringify()

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

class UserData(dict):
    def __init__(self, mapping): # type: (dict) -> None
        super(UserData, self).__init__(mapping)

    def parse(self): # type: () -> NBT
        '''返回当前UserData的NBT对象'''
        def parse_value(value):
            return _value_types[value['__type__']](value['__value__'])

        def parse_list(value):
            if isinstance(value, list):
                if len(value) == 0:
                    return tag.List([])
                elif isinstance(value[0], dict) and list(value[0].keys()) == ['__type__', '__value__']:
                    return tag.List([parse_value(x) for x in value])
                elif isinstance(value[0], list):
                    return tag.List([parse_list(x) for x in value])
                elif isinstance(value[0], dict):
                    return tag.List([parse_dict(x) for x in value])
            else:
                print(value)
                return _arr_types[value['__type__']](value['__value__'])
            
        def parse_dict(value):
            result = {}
            for k, v in value.items():
                k = str(k)
                if isinstance(v, dict) and list(v.keys()) == ['__type__', '__value__']:
                    result[k] = parse_list(v) if v['__type__'] in {7, 11, 12} else parse_value(v)
                elif isinstance(v, list):
                    result[k] = parse_list(v)
                elif isinstance(v, dict):
                    result[k] = parse_dict(v)
            return tag.Compound(result)
        
        return NBT(parse_dict(self))


_characters = {'{', '}', '[', ']', ':', ',', ';'}
_ignores = {' ', '\t', '\n', '\r'}
_data_types = {
    'b': tag.Byte,
    's': tag.Short,
    'i': tag.Int,
    'l': tag.Long,
    'f': tag.Float,
    'd': tag.Double
}
_data_arr_types = {
    'B': tag.ByteArray,
    'I': tag.IntArray,
    'L': tag.LongArray
}
_enchantment_ids = {
    'protection': 0,
    'fire_protection': 1,
    'feather_falling': 2,
    'blast_protection': 3,
    'projectile_protection': 4,
    'thorns': 5,
    'respiration': 6,
    'depth_strider': 7,
    'aqua_affinity': 8,
    'sharpness': 9,
    'smite': 10,
    'bane_of_arthropods': 11,
    'knockback': 12,
    'fire_aspect': 13,
    'looting': 14,
    'efficiency': 15,
    'silk_touch': 16,
    'unbreaking': 17,
    'fortune': 18,
    'power': 19,
    'punch': 20,
    'flame': 21,
    'infinity': 22,
    'luck_of_the_sea': 23,
    'lure': 24,
    'frost_walker': 25,
    'mending': 26,
    'binding_curse': 27,
    'vanishing_curse': 28,
    'impaling': 29,
    'riptide': 30,
    'loyalty': 31,
    'channeling': 32,
    'multishot': 33,
    'piercing': 34,
    'quick_charge': 35,
    'soul_speed': 36,
    'swift_sneak': 37
}

def _parse_list(key, value): # type: (str, list) -> list
    try:
        k_ = key
        if isinstance(value[0], _strs) and value[0].startswith('__') and value[0].endswith('__'): # array
            result = {'__type__': _data_arr_types[value[0].strip('__')].tag_id, '__value__': []}
            for i, v in enumerate(value[1:]):
                k_ = '%s[%s]' % (key, i)
                _check_int_valid(v)
                result['__value__'].append(v['__value__'])
        else:
            result = []
            for i, v in enumerate(value):
                k_ = '%s[%s]' % (key, i)
                vtype = v['__type__'] if isinstance(v, dict) and v.keys() == ['__type__', '__value__'] else type(v)
                if i == 0:
                    ltype = vtype
                elif ltype != vtype:
                    raise NBTStoreError('设置的数据 %s 类型与列表类型不匹配' % UserData(v).parse())
                
                if vtype == list:
                    result.append(_parse_list(k_, v))
                elif vtype == dict:
                    result.append(_parse_compound(k_, v))
                elif isinstance(v, _strs):
                    result.append({'__type__': 8, '__value__': v})
                else:
                    _check_int_valid(v)
                    result.append({'__type__': v['__type__'], '__value__': v['__value__']} if isinstance(vtype, int) else v)
        return result
    except Exception as e:
        _raise(e, k_)
        
def _parse_compound(key, value): # type: (str, dict) -> dict
    try:
        result = {}
        for k, v in value.items():
            k_ = '%s.%s' % (key, k)
            k = str(k)
            if isinstance(v, _strs):
                result[k] = {'__type__': 8, '__value__': v}

            elif isinstance(v, list):
                result[k] = _parse_list(k_, v)

            elif isinstance(v, dict):
                if v.keys() == ['__type__', '__value__']:
                    _check_int_valid(v)
                    result[k] = {'__type__': v['__type__'], '__value__': v['__value__']}
                else:
                    result[k] = _parse_compound(k_, v)
            else:
                result[k] = {'__type__': v['__type__'], '__value__': v['__value__']}
        return result
    except Exception as e:
        _raise(e, key)

def parse_snbt(value): # type: (str) -> UserData
    '''
    将SNBT解析为UserData对象
    '''
    if value[0] + value[-1] != '{}':
        raise NBTParseError('NBT解析失败: 无效的 SNBT')
    if value[0] + value[-1] == '{}' and value[1:-1].strip() == '':
        return NBT({})
    in_string, quote_type = False, 0
    last = [None, False, False, False]
    parts, add = [], ''
    for index, t in enumerate(value):
        if not in_string:
            if t in _ignores:
                continue

            is_character = t in _characters
            is_num = t in '-+0123456789.' and (last[0] in _characters or last[3])
            if t in 'BIL' and last[0] == '[' and value[index + 1] == ';':
                is_character = True
            if t in 'bBsSlLfFdDEe' and last[0] in '-+0123456789.': 
                is_num = True
        if t == '"' and quote_type != 1 and last[0] != '\\':
            quote_type = 2
            in_string = not in_string
            if in_string is False:
                quote_type = 0
                parts.append([add + t, True, False, False])
                add = ''
                continue
        elif t == "'" and quote_type != 2 and last[0] != '\\':
            quote_type = 1
            in_string = not in_string
            if in_string is False:
                quote_type = 0
                parts.append([add + t, True, False, False])
                add = ''
                continue
        
        if [in_string, is_character, is_num] == last[1:]:
            add += t
        else:
            # TODO: 语法分析器的活
            if add[-3:] in ('[B;', '[I;', '[L;'):
                add = add[:-3] + '["__%s__", ' % add[-2]
            parts.append([add, last[1], last[2], last[3]])
            add = t
        
        last = [t, in_string, is_character, is_num]
    parts.append([add, last[1], last[2], last[3]])

    last = [None, False, False, False]
    json_string = ''
    for index, part in enumerate(parts[1:]):
        if part[0] == '':
            continue
        if index == 0:
            json_string += '{'
            last = part
            continue

        add, in_string, is_character, is_num = part
        add = add.replace('\n', r'\n')
        if in_string:
            json_string += add if add[0] == '"' else '"%s"' % add[1:-1].replace(r"\'", "'").replace('"', r'\"')
        else:
            if add in ('+', '-'):
                json_string += '"%s"' % add
            elif is_num and not any(x.isdigit() for x in add):
                json_string += '"%s"' % add
            elif add == 'true':
                json_string += '{"__type__": 1, "__value__": 1}'
            elif add == 'false':
                json_string += '{"__type__": 1, "__value__": 0}'
            elif is_num and last[2]:
                json_string += ('{"__type__": %s, "__value__": %s}' % (_data_types[add[-1].lower()].tag_id, add[:-1])) if add[-1].isalpha() else ('{"__type__": 3, "__value__": %s}' % add)
            elif is_character != last[2] and not last[1] and not last[3] and last[0] not in ('true', 'false'):
                json_string += '"%s' % add
            else:
                json_string += add

        last = part

    try:
        result = _parse_compound('', _loads(json_string))
        ########
        if result.get('ench'):
            for index, ench in enumerate(result['ench']):
                eid = ench.get('id').get('__value__')
                if not isinstance(eid, _strs):
                    continue
                ench_id = _enchantment_ids.get(eid.replace('minecraft:', ''))
                if ench_id: result['ench'][index]['id'] = {'__type__': 2, '__value__': ench_id}
        ########
        return UserData(result)
    except ValueError as e:
        e_ = e
        e = str(e)
        if e[:6] in ['Expect', 'Unterm', 'No JSO']:
            errors = {
                'No JSON object could be decoded': '无效的 SNBT',
                'Unterminated string starting at:': 'String没有以预期的方式终止',
                'Expecting property name enclosed in double quotes:': '期望一个String',
                'Expecting property name:': '期望一个值',
                'Expecting : delimiter:': "缺少 ':' ",
                'Expecting object:': '期望一个Compound',
                'Expecting , delimiter:': "缺少 ',' "
            }
            for starts, errmsg in errors.items():
                if e.startswith(starts):
                    raise NBTParseError('SNBT解析错误: %s' % errmsg)
            raise e_

def parse_item_format(value): # type: (str | NBT) -> dict
    if isinstance(value, str):
        value = parse_snbt(value)
        if 'Name' not in value.keys():
            raise ItemFormatParseError('物品共通标签缺少标签: id')
        if 'Count' not in value.keys():
            raise ItemFormatParseError('物品共通标签缺少标签: Count')
    cache = value.copy()
    id_ = cache.get('Name', '')
    return {
            'newItemName': ('minecraft:%s' % id_) if ':' not in id_ else id_,
            'count': int(cache.get('Count', 0)),
            'newAuxValue': int(cache.get('Damage', 0)),
            'userData': NBT(cache.get('tag', {})).parse()
        }

def parse_itemDict(value): # type: (dict) -> NBT
    cache = value.copy()
    return NBT({
        'Name': tag.String(cache['newItemName']),
        'Count': tag.Byte(cache['count']),
        'Damage': tag.Short(cache['newAuxValue']),
        'tag': tag.Compound(UserData(cache['userData']).parse())
    })
        

if __name__ == '__main__':
    s = '''
{Byte:1b,Boolean:true,Short:1s,Int:1,Long:1l,Float:1.1f,Double:3.0002d,String:'aaa',ListInt:[1,2,3,4],ListStr:[asd,awd],ListFloat:[1f,23.44f],Compound:{A:1,B:{C:1}},ByteArray:[B;1b,2b,false,true],IntArray:[I;1,2,3,4],LongArray:[L;1l,2l,3l]}
'''.strip()
    print(parse_snbt(s))