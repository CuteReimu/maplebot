"""药水效率表格"""
import logging

from maplebot.utils.charts import render_table
from maplebot.utils.config import level_exp_data

logger = logging.getLogger("maplebot.potion")


def calculate_potion() -> str | None:
    """生成 8421 药水效率表格，返回 base64 图片"""
    potions = {
        "敲头": int(level_exp_data.get("data.199", 0) or 0),
        "209药": int(level_exp_data.get("data.209", 0) or 0),
        "219药": int(level_exp_data.get("data.219", 0) or 0),
        "229药": int(level_exp_data.get("data.229", 0) or 0),
        "239药": int(level_exp_data.get("data.239", 0) or 0),
        "249药": int(level_exp_data.get("data.249", 0) or 0),
        "259药": int(level_exp_data.get("data.259", 0) or 0),
        "269药": int(level_exp_data.get("data.269", 0) or 0),
    }
    keys = ["敲头", "209药", "219药", "229药", "239药", "249药", "259药", "269药"]

    data: list[list[str]] = []
    for i in range(201, 241):
        row: list[str] = [str(i)]
        for key in keys:
            value = potions[key]
            need = int(level_exp_data.get(f"data.{i}", 0) or 0)
            v = min(100.0, value / need * 100) if need > 0 else 0.0
            row.append(f"{v:.2f}%")
        # 右侧: i+40
        row.append(str(i + 40))
        for key in keys:
            value = potions[key]
            need = int(level_exp_data.get(f"data.{i + 40}", 0) or 0)
            v = min(100.0, value / need * 100) if need > 0 else 0.0
            row.append(f"{v:.2f}%")
        data.append(row)

    header = ["等级"] + keys + ["等级"] + keys

    # 单元格上色: 每隔 9 列(等级列)灰色，>50% 且前一列 2 倍以上粉色
    n_cols = len(header)
    n_rows = len(data)
    cell_colors: list[list[str | None]] = []
    for ri in range(n_rows):
        row_colors: list[str | None] = []
        for ci in range(n_cols):
            if ci % 9 == 0:
                row_colors.append("#b4b4b480")
            elif ci > 1:
                text = data[ri][ci]
                try:
                    val = float(text.rstrip("%"))
                except ValueError:
                    row_colors.append(None)
                    continue
                if val >= 50:
                    prev_text = data[ri][ci - 1]
                    try:
                        prev_val = float(prev_text.rstrip("%"))
                    except ValueError:
                        prev_val = 0
                    if prev_val > 0 and val > prev_val * 2:
                        row_colors.append("#FF82AB80")
                    else:
                        row_colors.append(None)
                elif ci == n_cols - 1:
                    row_colors.append("#FF82AB80")
                else:
                    row_colors.append(None)
            else:
                row_colors.append(None)
        cell_colors.append(row_colors)

    try:
        return render_table(
            header=header,
            data=data,
            width=1600,
            cell_colors=cell_colors,
        )
    except Exception as e:
        logger.error("render chart failed: %s", e)
        return None
