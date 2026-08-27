from urllib.parse import quote

from nonebot import on_type
from nonebot.adapters.qq import InteractionCreateEvent, Event
from nonebot.adapters.qq.message import MessageSegment
from nonebot.adapters.qq.models.common import MessageKeyboard, InlineKeyboard, InlineKeyboardRow, Button, RenderData, \
    Action, Permission
from nonebot.rule import Rule


def input_link(show: str, text: str | None = None) -> str:
    """
    蓝色超链接状的文本，点击后可以在输入框中自动输入指定文字。只能在markdown类型消息中使用。

    Args:
        show: 显示的文本
        text: 自动输入的文字将会是 @bot text，不填则为显示的文本加一个空格

    Examples:
        .. code-block:: python

            MessageSegment.markdown(f'请先{input_link("注册")}')
    """
    text = text or show + ' '
    return f'<qqbot-cmd-input text="{quote(text)}" show="{quote(show)}" />'


def button_rows(
        btnss: list[list[str]],
        style: int | None = None,
        button_type: int | None = None,
        data: list[list[str]] | None = None,
) -> MessageSegment:
    """
    按钮，只能接在markdown类型消息之后

    Args:
        btnss: 按钮上显示的文字，二维数组，最多 5x5
        style: 按钮样式，0=灰线框, 1=蓝线框, 2=白字, 3=蓝底白字
        button_type: - 0：跳转按钮：http 或 小程序
            - 1：回调按钮：回调后台接口, data 传给后台, 需要使用 :func:`on_button_callback` 注册回调
            - 2：指令按钮：自动在输入框插入 @bot data
        data: 回调数据。type=1/2 时才有用。不填则表示使用对应在 btnss 里的值

    Examples::
        .. code-block:: python

            m = Message()
            m += MessageSegment.markdown("请选择")
            m += button_rows([["按钮1", "按钮2"]], type=2)
    """
    all_btns: list[InlineKeyboardRow] = []
    n = 0
    for i, btns in enumerate(btnss):
        btn_row: list[Button] = []
        for j, btn in enumerate(btns):
            n += 1
            btn_row.append(Button(
                id=f"button_{n}",
                render_data=RenderData(
                    label=btn,
                    style=style,
                ),
                action=Action(
                    type=button_type,
                    permission=Permission(type=2),
                    data=data[i][j] if data is not None else btn,
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
        button_type: int | None = None,
        data: list[str] | None = None,
) -> MessageSegment:
    """
    按钮，只能接在markdown类型消息之后

    Args:
        btns: 按钮上显示的文字，每行5个按钮，自动换行，最多5行25个按钮
        style: 按钮样式，0=灰线框, 1=蓝线框, 2=白字, 3=蓝底白字
        button_type: - 0：跳转按钮：http 或 小程序
            - 1：回调按钮：回调后台接口, data 传给后台, 需要使用 :func:`on_button_callback` 注册回调
            - 2：指令按钮：自动在输入框插入 @bot data
        data: 回调数据。button_type=1/2 时才有用。不填则表示使用对应在 btnss 里的值

    Examples::
        .. code-block:: python

            m = Message()
            m += MessageSegment.markdown("请选择")
            m += buttons(["按钮1", "按钮2"], type=2)
    """
    data = None if data is None else [data[i:i + 5] for i in range(0, len(data), 5)]
    return button_rows([btns[i:i + 5] for i in range(0, len(btns), 5)], style=style, button_type=button_type, data=data)


def _button_callback_rule(event: Event) -> bool:
    """Rule：@机器人且无其他有效内容（NoneBot2 已将 @bot 段剥离，直接检查剩余消息）"""
    if not isinstance(event, InteractionCreateEvent):
        return False
    return event.type == 11


def on_button_callback(priority=10, block=True):
    """注册一个按钮回调响应器，对应上述按钮的 :param:`type` 为1时的点击回调"""
    return on_type(InteractionCreateEvent, rule=Rule(_button_callback_rule), priority=priority, block=block)
