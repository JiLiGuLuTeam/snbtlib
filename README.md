# 我的世界中国版modapi可用的SNBT解析模块

## 使用方法

解析SNBT
```python
from snbtlib import parse_snbt
result = parse_snbt('{foo:bar}')
```
转换NBT对象为UserData对象
```python
from snbtlib import parse_snbt
result = parse_snbt('{foo:bar}')
result = result.parse()
```
在python代码中创建NBT对象
```python
from snbtlib.tag import *

# 创建一个整型
integer = Int(1)

# 创建一个单精度浮点数
number = Float(3.3)

# 创建一个列表
numbers = List[Int]([1, 2, 3, 4])

# 创建一个复合标签
comp = Compound({'test': Int(1)})
```
