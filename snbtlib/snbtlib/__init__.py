# -*- coding: utf-8 -*-
import __future__
import tag
from base import BaseNBTError, NBTParseError, NBTStoreError, ItemFormatParseError
import json

strs = (str, type(u''))
if not bool:
    long = type()

class NBT(tag.Compound):
    def stringify(self, highlight=False): # type: (bool) -> str
        '''返回SNBT'''
        h = (lambda color, value: ('§%s%s§f' % (color, value))) if highlight else (lambda color, value: value)
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
                if isinstance(v, (int, float, strs)):
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
                if isinstance(v, (int, float, strs)):
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
        def parse_data(value):
            return {'__type__': value.tag_id, '__value__': int(value) if isinstance(value, tag.BaseInteger) else float(value) if isinstance(value, float) else str(value)}
        def parse_array(value):
            if isinstance(value, tag.List):
                if len(value) == 0:
                    return []
                elif isinstance(value[0], list):
                    return [parse_array(x) for x in value]
                elif isinstance(value[0], dict):
                    return [parse_compound(x) for x in value]
                elif isinstance(value[0], (int, float, strs)):
                    return [parse_data(x) for x in value]
            else:
                return {'__type__': value.tag_id, '__value__': [int(x) for x in value]}

        def parse_compound(value):
            result = {}
            for k, v in value.items():
                k = str(k)
                if isinstance(v, (int, float, strs)):
                    result[k] = parse_data(v)
                elif isinstance(v, list):
                    result[k] = parse_array(v)
                elif isinstance(v, dict):
                    result[k] = parse_compound(v)
            return result
        
        return UserData(parse_compound(self))

    def __str__(self):
        return self.stringify()

class UserData(dict):
    def parse(self): # type: () -> NBT
        '''返回当前UserData的NBT对象'''
        def parse_value(value):
            types = {
                1: tag.Byte,
                2: tag.Short,
                3: tag.Int,
                4: tag.Long,
                5: tag.Float,
                6: tag.Double,
                8: tag.String
            }
            return types[value['__type__']](value['__value__'])

        def parse_list(value):
            if isinstance(value, list):
                if len(value) == 0:
                    return tag.List()
                elif isinstance(value[0], dict) and list(value[0].keys()) == ['__type__', '__value__']:
                    return tag.List([parse_value(x) for x in value])
                elif isinstance(value[0], list):
                    return tag.List([parse_list(x) for x in value])
                elif isinstance(value[0], dict):
                    return tag.List([parse_dict(x) for x in value])
            else:
                types = {
                    7: tag.ByteArray,
                    11: tag.IntArray,
                    12: tag.LongArray
                }
                return types[value['__type__']](value['__value__'])
            
        def parse_dict(value):
            result = {}
            for k, v in value.items():
                k = str(k)
                if isinstance(v, dict) and list(v.keys()) == ['__type__', '__value__']:
                    result[k] = parse_list(v) if v['__type__'] in (7, 11, 12) else parse_value(v)
                elif isinstance(v, list):
                    result[k] = parse_list(v)
                elif isinstance(v, dict):
                    result[k] = parse_dict(v)
            return tag.Compound(result)
        
        return NBT(parse_dict(self))


def parse_snbt(value):
    # type: (str) -> NBT
    '''
    将SNBT解析为NBT对象.
    '''
    characters = {'{', '}', '[', ']', ':', ',', ';'}
    ignores = {' ', '\t', '\n', '\r'}

    if value[0] + value[-1] != '{}':
        raise NBTParseError('无效的 SNBT')
    if value[0] + value[-1] == '{}' and value[1:-1].strip() == '':
        return NBT({})
    in_string, quote_type = False, 0
    last = [None, False, False, False]
    parts, add = [], ''
    for index, t in enumerate(value):
        if not in_string:
            if t in ignores:
                continue

            is_character = t in characters
            is_num = t in '-+0123456789.' and (last[0] in characters or last[3])
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
            # 这里干了语法分析器的活
            if add[-3:] in ('[B;', '[I;', '[L;'):
                add = add[:-3] + '["__%s__",' % add[-2]
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
                json_string += '["__b__",1]'
            elif add == 'false':
                json_string += '["__b__",0]'
            elif is_num and last[2]:
                json_string += ('["__%s__",%s]' % (add[-1].lower(), add[:-1])) if add[-1].isalpha() else ('["__i__",%s]' % add)
            elif is_character != last[2] and not last[1] and not last[3] and last[0] not in ('true', 'false'):
                json_string += '"%s' % add
            else:
                json_string += add

        last = part

    
    def parse_data(key, value): # type: (str, list) -> int | float | str
        try:
            if isinstance(value, strs):
                try:
                    return tag.String(str(value))
                except UnicodeEncodeError:
                    return tag.String()
            
            elif isinstance(value, list):# 数字
                types = {
                    'b': tag.Byte,
                    's': tag.Short,
                    'i': tag.Int,
                    'l': tag.Long,
                    'f': tag.Float,
                    'd': tag.Double
                }
                return types[value[0][2].lower()](value[1])
        except Exception as e:
            raise e if isinstance(e, NBTParseError) else NBTParseError('%s: %s, 出现在 %s ' % (e.translate, e.msg, key)) if isinstance(e, BaseNBTError) else NBTParseError('脚本层错误: %s, 出现在 %s\n如无法解决请联系作者并发送你的命令' % (e.args, key))

    def parse_array(key, value): # type: (str, list) -> list
        try:
            if len(value) == 0:
                return tag.List(value)
            if len(value) == 2 and value[0] == u'__l__' and isinstance(value[1], long):
                return tag.Long(value[1]) # 为什么会变成这样呢?
            if not all(type(x) == type(value[0]) for x in value):
                raise NBTStoreError('列表内数据类型错误')
            if isinstance(value[0], list) and isinstance(value[0][0], strs) and isinstance(value[0][1], list):
                return tag.List([parse_data('%s[%s]' % (key, i), x) for i, x in enumerate(value)])
            if isinstance(value[0], dict):
                return tag.List([parse_compound('%s[%s]' % (key, i), x) for i, x in enumerate(value)])
            if isinstance(value[0], strs) and len(value) >= 2 and isinstance(value[1], list):
                types = {
                    'B': tag.ByteArray,
                    'I': tag.IntArray,
                    'L': tag.LongArray
                }
                return types[value[0][2]]([parse_data('%s[%s]' % (key, i), x) for i, x in enumerate(value[1:])])
            return tag.List([parse_data('%s[%s]' % (key, i), x) for i, x in enumerate(value)])
        except Exception as e:
            raise e if isinstance(e, NBTParseError) else NBTParseError('%s: %s, 出现在 %s ' % (e.translate, e.msg, key)) if isinstance(e, BaseNBTError) else NBTParseError('脚本层错误: %s, 出现在 %s\n如无法解决请联系作者并发送你的命令' % (e.args, key))
        
    def parse_compound(key, value): # type: (str, dict) -> tag.Compound
        try:
            for k, v in value.items():
                k_ = '%s.%s' % (key, k)
                if isinstance(v, list) and len(v) == 2 and isinstance(v[0], strs) and isinstance(v[1], (int, float)):
                    value[k] = parse_data(k_, v)
                elif isinstance(v, list):
                    value[k] = parse_array(k_, v)
                elif isinstance(v, dict):
                    value[k] = parse_compound(k_, v)
                else:
                    value[k] = parse_data(k_, v)
            return tag.Compound(value)
        except Exception as e:
            raise e if isinstance(e, NBTParseError) else NBTParseError('%s: %s, 出现在 %s ' % (e.translate, e.msg, key)) if isinstance(e, BaseNBTError) else NBTParseError('脚本层错误: %s, 出现在 %s\n如无法解决请联系作者并发送你的命令' % (e.args, key))
    try:
        result = parse_compound('', json.loads(json_string))
        ########
        if result.get('id'):
            result['Name'] = result['id']
            del result['id']
        if result.get('ench'):
            for index, ench in enumerate(result['ench']):
                enchantment_ids = {
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
            try:
                ench_id = enchantment_ids.get(ench.get('Name').replace('minecraft:', ''))
                if ench_id: result['ench'][index]['Name'] = tag.Short(ench_id)
            except: pass
        ########
        return NBT(result)
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

def parse_item_format(value):
    # type: (str | NBT) -> dict
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

def parse_itemDict(value):
    # type: (dict) -> NBT
    cache = value.copy()
    return NBT({
        'Name': tag.String(cache['newItemName']),
        'Count': tag.Byte(cache['count']),
        'Damage': tag.Short(cache['newAuxValue']),
        'tag': tag.Compound(UserData(cache['userData']).parse())
    })
        

if __name__ == '__main__':
    pass