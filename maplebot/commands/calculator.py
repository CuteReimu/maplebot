from maplebot.utils.format_utils import format_int64

# (岛球， meso)
_arc_data = [
    (0, 0),
    (0, 0),
    (12, 970_000),
    (27, 2_200_000),
    (47, 3_860_000),
    (74, 6_120_000),
    (110, 9_180_000),
    (157, 13_220_000),
    (217, 18_440_000),
    (292, 25_040_000),
    (384, 33_220_000),
    (495, 43_210_000),
    (627, 55_220_000),
    (782, 69_480_000),
    (962, 86_220_000),
    (1_169, 105_670_000),
    (1_405, 128_090_000),
    (1_672, 153_720_000),
    (1_972, 182_820_000),
    (2_307, 215_650_000),
    (2_679, 252_470_000),
]

# (岛球， meso)
_sac_data = [
    (0, 0),
    (0, 0),
    (29, 41_700_000),
    (105, 146_500_000),
    (246, 332_600_000),
    (470, 614_800_000),
    (795, 1_004_800_000),
    (1_239, 1_510_900_000),
    (1_820, 2_138_300_000),
    (2_556, 2_889_000_000),
    (3_465, 3_761_600_000),
    (4_565, 4_751_600_000),
]

# 技能、精通、通用、五转
# (大核，小核)
_hexa_data = [
    # 技能核心
    [
        (0, 0),
        (0, 0),
        (1, 30),
        (2, 65),
        (3, 105),
        (5, 150),
        (7, 200),
        (9, 255),
        (12, 315),
        (15, 380),
        (25, 580),
        (28, 660),
        (31, 750),
        (35, 850),
        (39, 960),
        (43, 1_080),
        (47, 1_210),
        (51, 1_350),
        (55, 1_500),
        (60, 1_660),
        (75, 2_010),
        (80, 2_180),
        (85, 2_360),
        (90, 2_550),
        (95, 2_750),
        (100, 2_960),
        (106, 3_180),
        (112, 3_410),
        (118, 3_650),
        (125, 3_900),
        (145, 4_400),
    ],
    # 精通核心
    [
        (0, 0),
        (3, 50),
        (4, 65),
        (5, 83),
        (6, 103),
        (7, 126),
        (8, 151),
        (9, 179),
        (11, 209),
        (13, 242),
        (18, 342),
        (20, 382),
        (22, 427),
        (24, 477),
        (26, 532),
        (28, 592),
        (30, 657),
        (32, 727),
        (34, 802),
        (37, 882),
        (45, 1_057),
        (48, 1_142),
        (51, 1_232),
        (54, 1_327),
        (57, 1_427),
        (60, 1_532),
        (63, 1_642),
        (66, 1_757),
        (69, 1_877),
        (73, 2_002),
        (83, 2_252),
    ],
    # 强化核心
    [
        (0, 0),
        (4, 75),
        (5, 98),
        (6, 125),
        (7, 155),
        (9, 189),
        (11, 227),
        (13, 269),
        (16, 314),
        (19, 363),
        (27, 513),
        (30, 573),
        (33, 641),
        (36, 716),
        (39, 799),
        (42, 889),
        (45, 987),
        (48, 1_092),
        (51, 1_205),
        (55, 1_325),
        (67, 1_588),
        (71, 1_716),
        (75, 1_851),
        (79, 1_994),
        (83, 2_144),
        (87, 2_302),
        (92, 2_467),
        (97, 2_640),
        (102, 2_820),
        (108, 3_008),
        (123, 3_383),
    ],
    # 通用核心
    [
        (0, 0),
        (7, 125),
        (9, 163),
        (11, 207),
        (13, 257),
        (16, 314),
        (19, 377),
        (22, 446),
        (27, 521),
        (32, 603),
        (46, 903),
        (51, 1_013),
        (56, 1_137),
        (62, 1_275),
        (68, 1_427),
        (74, 1_592),
        (80, 1_771),
        (86, 1_964),
        (92, 2_171),
        (99, 2_391),
        (116, 2_916),
        (123, 3_150),
        (130, 3_398),
        (137, 3_660),
        (144, 3_935),
        (151, 4_224),
        (160, 4_527),
        (169, 4_844),
        (178, 5_174),
        (188, 5_518),
        (208, 6_268),
    ],
    # 通用五转
    [
        (0, 0),
        (4, 90),
        (5, 115),
        (6, 145),
        (7, 180),
        (9, 220),
        (11, 265),
        (13, 315),
        (16, 370),
        (19, 430),
        (28, 610),
        (31, 683),
        (34, 764),
        (37, 854),
        (40, 952),
        (44, 1_059),
        (48, 1_174),
        (52, 1_298),
        (56, 1_430),
        (60, 1_571),
        (74, 1_886),
        (78, 2_037),
        (83, 2_197),
        (88, 2_367),
        (93, 2_546),
        (98, 2_735),
        (103, 2_933),
        (108, 3_141),
        (113, 3_358),
        (119, 3_585),
        (137, 4_035),
    ]
]


def get_culmulative_cost(name: str, start: int, end: int) -> tuple[int, int]:
    if name == "arc":
        data = _arc_data
    elif name == "sac":
        data = _sac_data
    elif name == "hexa_skill":
        data = _hexa_data[0]
    elif name == "hexa_mastery":
        data = _hexa_data[1]
    elif name == "hexa_boost":
        data = _hexa_data[2]
    elif name == "hexa_common":
        data = _hexa_data[3]
    elif name == "hexa_common_5th":
        data = _hexa_data[4]
    else:
        raise ValueError(f"Unknown cost type: {name}")

    if (start < 0 or end < 0) or (start >= len(data) or end >= len(data)):
        raise ValueError(f"Invalid start or end level: {start}, {end}")

    start_costs = data[start]
    end_costs = data[end]

    return (end_costs[0] - start_costs[0], end_costs[1] - start_costs[1])


def calculate_arc_cost(start: int = 1, end: int = 20) -> str:
    """计算arc从 start 级升级到 end 级需要的岛球和金币"""

    symbol, meso = get_culmulative_cost("arc", start, end)
    _ = format_int64(meso)
    msg = f"神秘{start}级升级到 {end} 级需要： {symbol}岛球"
    return msg


def calculate_sac_cost(start: int = 1, end: int = 11) -> str:
    """计算sac从 start 级升级到 end 级需要的岛球和金币"""

    symbol, meso = get_culmulative_cost("sac", start, end)
    _ = format_int64(meso)
    msg = f"原初{start}级升级到 {end} 级需要：{symbol}岛球"
    return msg


def calculate_hexa_cost(hexa_type: str, start: int = 0, end: int = 30) -> str:
    """计算六转从 start 级升级到 end 级需要的大核和小核"""
    if hexa_type not in ["技能", "精通", "强化", "通用", "通用五转"]:
        raise ValueError(f"Unknown hexa type: {hexa_type}")
    idx = ["技能", "精通", "强化", "通用", "通用五转"].index(hexa_type)
    erda, fragment = get_culmulative_cost(
        f"hexa_{['skill', 'mastery', 'boost', 'common', 'common_5th'][idx]}", start, end
    )
    if hexa_type == "技能" and start == 0:
        msg = f"{hexa_type}核心 {start} 级到 {end}级 需要：{erda} 大核 和 {fragment} 小核, 不含解锁的5大核和100小核"
    else:
        msg = f"{hexa_type}核心 {start} 级到 {end}级 需要：{erda} 大核 {fragment} 小核"
    return msg


HEXA_SAMPLE_INPUT = """计算六转进度 #修改后直接发送
[技能H1]      目标 30 / 当前 0
[技能H2]      目标 30 / 当前 0
[精通1]       目标 30 / 当前 0
[精通2]       目标 30 / 当前 0
[精通3]       目标 30 / 当前 0
[精通4]       目标 30 / 当前 0
[V强化1]      目标 30 / 当前 0
[V强化2]      目标 30 / 当前 0
[V强化3]      目标 30 / 当前 0
[V强化4]      目标 30 / 当前 0
[通用1]       目标 30 / 当前 0
[通用2]       目标 30 / 当前 0
[通用3(五转)] 目标 30 / 当前 0
"""


def parse_hexa_progress_input(input_str: str) -> dict[str, list[int]]:
    """解析六转进度输入字符串，返回字典"""
    hexa_dict = {}
    input_str = input_str.replace("---", "\n")
    lines = input_str.strip().split("\n")
    for line in lines:
        if ']' not in line:
            continue
        parts = line.split(']')
        _name = parts[0].split('[')[-1].strip()
        if "技能" in _name:
            name = "技能"
        elif "精通" in _name:
            name = "精通"
        elif "强化" in _name:
            name = "强化"
        elif "通用" in _name:
            name = "通用"
            if "五转" in _name:
                name = "通用五转"
        else:
            raise ValueError(f"Unknown hexa name: {_name}")

        if name not in hexa_dict:
            hexa_dict[name] = []

        def _parse(s):
            digits =  "".join(c for c in s if c.isdigit())
            if digits == "":
                raise ValueError(f"Wrong input {s}")
            return int(digits)

        goal, current = parts[1].split("/")
        goal, current = _parse(goal), _parse(current)

        hexa_dict[name].append([current, goal])
    return hexa_dict


def calculate_hexa_progress(hexa_dict: dict[str, list[int]]) -> str:
    """计算六转各类型核心的进度"""
    total_costs = [0, 0]
    current_spent = [0, 0]
    substrings = []

    def divPer(num1, num2):
        if num2 == 0 or num1 == num2:
            return "100%"
        return f"{num1 / num2 * 100:.1f}%"

    for hexa_type, levels in hexa_dict.items():
        if hexa_type not in ["技能", "精通", "强化", "通用", "通用五转"]:
            raise ValueError(f"Unknown hexa type: {hexa_type}")
        idx = ["技能", "精通", "强化", "通用", "通用五转"].index(hexa_type)
        for i, level in enumerate(levels):
            current, goal = level
            if current > goal:
                continue
            erda_current, fragment_current = get_culmulative_cost(
                f"hexa_{['skill', 'mastery', 'boost', 'common', 'common_5th'][idx]}", 
                0,
                current
            )
            erda_goal, fragment_goal = get_culmulative_cost(
                f"hexa_{['skill', 'mastery', 'boost', 'common', 'common_5th'][idx]}", 
                0,
                goal
            )
            total_costs[0] += erda_goal
            total_costs[1] += fragment_goal
            current_spent[0] += erda_current
            current_spent[1] += fragment_current
            substrings.append(f"{hexa_type}{i+1} {current}/{goal}: {erda_current}/{erda_goal}大核({divPer(erda_current, erda_goal)}) {fragment_current}/{fragment_goal}小核({divPer(fragment_current, fragment_goal)})")
        substrings.append('')
    if total_costs[0] == 0 and total_costs[1] == 0:
        return "没有追求的人查什么进度"
    msg = f"总需求：{total_costs[0]} 大核 {total_costs[1]} 小核\n" + \
          f"已消耗：{current_spent[0]} 大核 {current_spent[1]} 小核\n" + \
          f"剩余：{total_costs[0] - current_spent[0]} 大核 {total_costs[1] - current_spent[1]} 小核\n" + \
          f"总进度： {divPer(current_spent[0], total_costs[0])}大核, {divPer(current_spent[1], total_costs[1])}小核\n" + \
          "详细进度：\n    " + "\n    ".join(substrings)
    return msg
