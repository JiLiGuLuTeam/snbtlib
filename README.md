# snbtlib

我的世界中国版 ModSDK(Python 2.7)可用的 SNBT / NBT 解析库,以**前置模组**的形式放入行为包根目录使用。

## 安装

把本仓库整个目录放到行为包根目录下,目录名保持 `snbtlib`,与你自己的模组目录同级:

```
behavior_pack_xxx/
    snbtlib/
        __init__.py
        base.py
        tag.py
        modMain.py
    你的模组/
        modMain.py
```

`modMain.py` 用 `@Mod.Binding(name="snbtlib")` 注册为一个不含任何 System 的空模组,只负责让 `snbtlib` 包随行为包一起被引擎加载,
你的模组里直接 `import snbtlib` 即可。

## 使用

解析 SNBT 字符串为 NBT 对象
```python
from snbtlib import parse_snbt
comp = parse_snbt('{foo:"bar",count:3b,pos:[I;1,2,3]}')
```

物品字典 / 物品格式串互转
```python
from snbtlib import parse_item_format, parse_itemDict, deserialize_nbt_dict
comp = parse_itemDict(item_dict)          # 引擎物品字典 -> Compound
item = parse_item_format(comp)            # Compound / 格式串 -> 引擎物品字典
comp = deserialize_nbt_dict(user_data)    # 引擎 userData 字典 -> Compound
```

在 Python 代码中直接构造 NBT 对象
```python
from snbtlib.tag import *

integer = Int(1)
number = Float(3.3)
numbers = List[Int]([1, 2, 3, 4])
comp = Compound({"test": Int(1)})
```

## 许可证

Apache License 2.0,见 `LICENSE`。
