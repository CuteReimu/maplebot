from urllib.parse import quote

from nonebot import on_type
from nonebot.adapters.qq import InteractionCreateEvent, Event
from nonebot.adapters.qq.message import MessageSegment
from nonebot.adapters.qq.models.common import MessageKeyboard, InlineKeyboard, InlineKeyboardRow, Button, RenderData, \
    Action, Permission
from nonebot.rule import Rule


def input_link(show: str, text: str | None = None) -> str:
    text = text or show + ' '
    return f'<qqbot-cmd-input text="{quote(text)}" show="{quote(show)}" />'


def button_rows(
        btnss: list[list[str]],
        style: int | None = None,
        type: int | None = None,
) -> MessageSegment:
    all_btns: list[InlineKeyboardRow] = []
    i = 0
    for btns in btnss:
        btn_row: list[Button] = []
        for btn in btns:
            btn_row.append(Button(
                id=f"button_{i}",
                render_data=RenderData(
                    label=btn,
                    style=style,
                ),
                action=Action(
                    type=type,
                    permission=Permission(type=2),
                    data=btn,
                )
            ))
        all_btns.append(InlineKeyboardRow(buttons=btn_row))
    return MessageSegment.keyboard(MessageKeyboard(
        content=InlineKeyboard(
            rows=all_btns
        )
    ))


def buttons(
        btns: list[str],
        style: int | None = None,
        type: int | None = None,
) -> MessageSegment:
    # 每行最多 5 个按钮
    return button_rows([btns[i:i + 5] for i in range(0, len(btns), 5)], style=style, type=type)


def _button_callback_rule(event: Event) -> bool:
    """Rule：@机器人且无其他有效内容（NoneBot2 已将 @bot 段剥离，直接检查剩余消息）"""
    if not isinstance(event, InteractionCreateEvent):
        return False
    return event.type == 11


def on_button_callback(priority=10, block=True):
    return on_type(InteractionCreateEvent, rule=Rule(_button_callback_rule), priority=priority, block=block)
