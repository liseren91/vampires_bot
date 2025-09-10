from typing import List

from db.models import ActionStatus
from keyboards.spec import KeyboardSpec, KeyboardParams, RowOrName


def main_menu_kb() -> KeyboardSpec:
    return KeyboardSpec(
        type="inline",
        name="main_menu",
        options=["actions", "map", "news", "profile", "help"],
        params=KeyboardParams(max_in_row=2),
    )


def actions_menu_kb() -> KeyboardSpec:
    return KeyboardSpec(
        type="inline",
        name="actions_menu",
        options=["defend", "attack", "scout", "communicate", "ritual", ["actions_list"], ["back"]],
        params=KeyboardParams(max_in_row=2)
    )


def district_list_kb() -> KeyboardSpec:
    return KeyboardSpec(
        type="inline",
        name="district_list_menu",
        options=[["prev", "next"], ["back"]],
        params=KeyboardParams(max_in_row=2),
        button_params={}
    )


def action_district_list_kb(action) -> KeyboardSpec:
    return KeyboardSpec(
        type="inline",
        name="action_district_menu",
        options=[["prev", "pick", "next"], ["back"]],
        params=KeyboardParams(max_in_row=2),
        button_params={
            "prev": {"action": action},
            "pick": {"action": action},
            "next": {"action": action},
            # "back" — без параметров
        },
    )


def action_setup_kb(
    resources: List[str],
    action_id: int,
    action_status: ActionStatus | str,
    *,
    communicate: bool = False,
    is_help: bool = False,
    is_list: bool = False,           # <--- НОВОЕ
    show_ideology_direction: bool = False,  # <--- NEW for ideology direction
) -> KeyboardSpec:
    """
    Строит inline-клавиатуру для настройки действия.
    В режиме is_list добавляет кнопки prev/next для листания экшенов.
    """
    rows: List[RowOrName] = []

    # ---- основное содержимое по статусу ----
    if action_status is ActionStatus.DRAFT or action_status == "draft":
        if not communicate:
            if not is_help:
                rows.append(["collective", "individual"])
            for res in resources:
                res = res.strip()
                if res:
                    rows.append([f"{res}_remove", res, f"{res}_add"])
            # Add ideology direction buttons for influence in attack/defend actions
            if show_ideology_direction:
                rows.append(["ideology_conservative", "ideology_reforms"])
            rows.append(["moving_on_point"])
            rows.append(["done"])
            rows.append(["delete", "back"])
        else:
            for res in resources:
                res = res.strip()
                if res:
                    rows.append([f"{res}_remove", res, f"{res}_add"])
            rows.append(["done"])
            rows.append(["delete", "back"])

    elif action_status is ActionStatus.PENDING or action_status == "pending":
        if not communicate:
            rows.append(["edit"])
            rows.append(["delete", "back"])
        else:
            rows.append(["back"])
    else:
        rows.append(["back"])

    # ---- навигация списка ----
    if is_list:
        # вставим навигацию в начало, чтобы она была всегда под рукой
        rows.insert(0, ["prev", "next"])

    # ---- параметры кнопок ----
    # по умолчанию всем прокидываем action_id
    butns_kwargs: dict[str, dict] = {btn: {"action_id": action_id, "is_list": is_list} for btn in sum(rows, [])}
    if is_list:
        # навигации нужен только флаг is_list
        butns_kwargs["prev"] = {"is_list": True}
        butns_kwargs["next"] = {"is_list": True}

    return KeyboardSpec(
        type="inline",
        name="action_setup_menu",
        options=rows,
        params=KeyboardParams(max_in_row=3),
        button_params=butns_kwargs,
    )



def scout_choice_kb() -> KeyboardSpec:
    rows: List[RowOrName] = [["scout_district", "scout_info"], ["back"]]
    button_params = {
        "scout_district": {"action": "scout"},
        "scout_info": {"action": "scout"},
        # "back" без payload
    }
    return KeyboardSpec(
        type="inline",
        name="scout_menu",
        options=rows,
        params=KeyboardParams(max_in_row=2),
        button_params=button_params,
    )


def scout_info_kb() -> KeyboardSpec:
    return KeyboardSpec(
        type="inline",
        name="scout_info",
        options=[["back"]],  # одна кнопка назад
        params=KeyboardParams(max_in_row=1),
        button_params={}
    )


def communicate_kb() -> KeyboardSpec:
    # одна кнопка "back"
    return KeyboardSpec(
        type="inline",
        name="communicate_prompt",
        options=[["back"]],
        params=KeyboardParams(max_in_row=1),
    )


def news_list_kb(disabled: bool = False) -> KeyboardSpec:
    # prev/next, затем back
    opts = [["prev", "next"], ["back"]]
    # Можно, если надо, отключать prev/next когда disabled=True
    if disabled:
        opts = [["back"]]
    return KeyboardSpec(
        type="inline",
        name="news_list_menu",
        options=opts,
        params=KeyboardParams(max_in_row=2),
    )