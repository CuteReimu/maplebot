# maplebot (Python 版)

GMSR 群机器人，基于 [NoneBot2](https://github.com/nonebot/nonebot2) + OneBot 11 协议。

## 开始

在项目根目录运行：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python bot.py
```

## 项目结构

```
python/
├── bot.py                          # NoneBot2 入口
├── .env                            # NoneBot2 配置
├── requirements.txt                # Python 依赖
└── maplebot/
    ├── __init__.py
    ├── plugins/
    │   └── maplebot_main.py        # 主插件（命令路由）
    ├── commands/
    │   ├── arc_more_damage.py      # ARC 神秘压制表格
    │   ├── boss_party.py           # Boss 开车订阅
    │   ├── cube.py                 # 魔方概率计算
    │   ├── find_role.py            # 角色查询
    │   ├── gen_table.py            # 通用表格生成
    │   ├── level_exp.py            # 等级经验计算
    │   ├── potion.py               # 药水效率表格
    │   └── star_force.py           # 升星模拟
    ├── utils/
    │   ├── charts.py               # 图表生成 (matplotlib)
    │   ├── class_name.py           # 职业名翻译
    │   ├── config.py               # 配置管理 (dynaconf)
    │   ├── db.py                   # KV 存储 (shelve)
    │   ├── dict_tfidf.py           # TF-IDF 分词 (jieba)
    │   └── perm.py                 # 权限检查
    └── data/
        └── cubeRates.json          # 魔方概率数据
```

## 依赖库

- OneBot SDK：NoneBot2
- 图表生成：matplotlib
- HTTP 请求：httpx
- 配置管理：dynaconf + PyYAML
- KV 数据库：shelve (内置)
- 中文分词：jieba
- JSON 解析：原生 dict

## 安装与运行

```bash
cd python/

# 1. 安装依赖
pip install -r requirements.txt

# 2. 修改配置
#    编辑 .env 中的 HOST/PORT
#    首次运行会在 config/maplebot/ 下生成默认 Config.yml
#    修改其中的 qq_groups / admin 等字段

# 3. 启动
python bot.py
```

## 打包与部署

### 打包

```bash
# 基本用法（版本号默认为当前GMT时间）
bash pack.sh

# 指定版本号
bash pack.sh 1.0.0
```

脚本会将以下内容打包进 `dist/maplebot-<版本号>.tar.gz`：

| 内容                 | 说明     |
|--------------------|--------|
| `bot.py`           | 主入口    |
| `maplebot/`        | 源码包    |
| `requirements.txt` | 依赖清单   |
| `.env.prod`        | 配置模板   |
| `start.sh`         | 一键启动脚本 |

### 部署

```bash
tar -xzf maplebot-1.0.0.tar.gz
cd maplebot-1.0.0

# 按需修改生产配置
# 首次运行前编辑 .env.prod，填入真实的 HOST/PORT/ONEBOT_WS_URLS 等
vim .env.prod

# 安装依赖
pip install --quiet -r requirements.txt

# 启动（脚本会自动安装依赖并以 prod 模式运行）
bash start.sh
```

`start.sh` 会自动设置 `ENVIRONMENT=prod`，

## 支持的命令

- `查看帮助` - 显示帮助列表
- `ping` - 测试连通性
- `roll [上限]` - 随机数
- `查询 游戏名` / `查询我` - 查询角色信息
- `绑定 游戏名` / `解绑` - 绑定/解绑角色
- `洗魔方 [部位] [等级]` - 魔方概率计算
- `模拟升星 等级 起始星 目标星 [七折] [减爆] [保护]` - 升星期望计算
- `爆炸次数` - 爆炸次数统计饼图
- `升级经验` / `升级经验 起始级 目标级` - 经验表/经验计算
- `8421` - 药水效率表
- `等级压制 等级差` - 等级压制计算
- `神秘压制` - ARC 伤害表
- `生成表格 CSV内容` - 自定义表格
- `我要开车 BOSS` / `订阅开车 BOSS` / `取消订阅` - Boss 开车
- `添加词条 名称` / `修改词条 名称` / `删除词条 名称` / `搜索词条 关键字` - 词条管理

## 注意事项

- OneBot 实现端（如 go-cqhttp / Lagrange 等）需要配置**反向 WebSocket** 连接到本程序
- `event.message_format` 需配置为 `array`
- Linux 环境下若中文乱码，需安装 `simhei.ttf` 字体
