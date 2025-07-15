# -*- coding: utf-8 -*-
import requests
import html
from datetime import datetime
from .logger import logger


def escape_html(text: str) -> str:
    """对 HTML 的特殊字符进行转义"""
    return html.escape(str(text))


def get_visual_width(s: str) -> int:
    """返回字符串的可视宽度，全角字符计为2，半角为1"""
    width = 0
    for char in s:
        if (
            "\u4e00" <= char <= "\u9fff"
            or "\u3040" <= char <= "\u30ff"
            or "\uac00" <= char <= "\ud7a3"
            or "\uff00" <= char <= "\uffef"
        ):
            width += 2
        else:
            width += 1
    return width


def send_checkin_report(results: list, config: dict):
    """
    格式化并发送签到报告
    :param results: 签到结果列表
    :param config: 全局配置字典
    """
    if not results or not config.get("notification", {}).get("telegram"):
        return

    today = datetime.now().strftime("%Y-%m-%d")
    site_width = 18
    status_width = 12

    MAX_ROWS_PER_MESSAGE = 30
    results_chunks = [
        results[i: i + MAX_ROWS_PER_MESSAGE]
        for i in range(0, len(results), MAX_ROWS_PER_MESSAGE)
    ]

    for i, chunk in enumerate(results_chunks):
        site_header, status_header, details_header = "站点", "状态", "详情"
        padded_site_header = site_header + " " * (
            site_width - get_visual_width(site_header)
        )
        padded_status_header = status_header + " " * (
            status_width - get_visual_width(status_header)
        )

        table_lines = [
            (
                f"{padded_site_header} | "
                f"{padded_status_header} | "
                f"{details_header}"
            ),
            f"{'-' * site_width} | {'-' * status_width} | {'-' * 10}",
        ]

        for result in chunk:
            site = escape_html(result["site_name"])
            status = escape_html(result["status"])
            details = escape_html(result.get("details", ""))

            padded_site = site + " " * (
                site_width - get_visual_width(site)
            )
            padded_status = status + " " * (
                status_width - get_visual_width(status)
            )

            table_lines.append(
                f"{padded_site} | {padded_status} | {details}"
            )

        table_content = "\n".join(table_lines)
        header_text = f"<b>PT站签到报告 ({today})</b>"
        if len(results_chunks) > 1:
            header_text += f"<b> (第 {i + 1}/{len(results_chunks)} 页)</b>"

        final_message = f"{header_text}\n<pre>{table_content}</pre>"
        send_telegram_message(final_message, config)


def send_telegram_message(message: str, config: dict):
    """
    通过 Telegram Bot 发送消息
    :param message: 要发送的消息内容
    :param config: 全局配置字典
    """
    try:
        notification_config = config.get('notification', {})
        telegram_config = notification_config.get('telegram', {})

        bot_token = telegram_config.get('bot_token')
        chat_id = telegram_config.get('chat_id')
        proxy = telegram_config.get('proxy')

        if not bot_token or not chat_id:
            logger.warning('Telegram bot_token 或 chat_id 未配置，跳过发送通知。')
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
        }

        proxies = {
            'http': proxy,
            'https': proxy
        } if proxy else None

        response = requests.post(
            url, json=payload, proxies=proxies, timeout=10
        )

        if response.status_code == 200:
            logger.info("Telegram 通知发送成功！")
        else:
            logger.error(
                f"Telegram 通知发送失败: {response.status_code} - {response.text}"
            )

    except Exception as e:
        logger.error(f"发送 Telegram 通知时发生错误: {e}")
