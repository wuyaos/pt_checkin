# -*- coding: utf-8 -*-
"""
cron: 30 8 * * *
new Env('PT站点自动签到');
"""

from pathlib import Path

try:
    from notify import send  # 青龙面板自动提供
except ImportError:
    # 如果青龙面板的notify不可用，使用本地版本
    def send(title: str, content: str):
        print(f"[通知] {title}")
        print(f"内容: {content}")
        print("-" * 50)

from pt_checkin.cli import run_signin, get_notification_message


def main():
    """主函数"""
    print("🚀 === PT站点自动签到开始 ===")

    # 配置文件路径（相对于当前脚本目录）
    current_dir = Path(__file__).parent
    config_file = current_dir / "config.yml"

    if not config_file.exists():
        error_msg = f"配置文件不存在: {config_file}"
        print(f"❌ {error_msg}")
        send("PT签到配置错误", error_msg)
        return

    # 执行签到
    result = run_signin(str(config_file))

    if not result['success']:
        error_msg = f"签到执行失败: {result['error']}"
        print(f"❌ {error_msg}")
        send("PT签到执行失败", error_msg)
        return

    # 获取通知消息（默认简单模式）
    notification = get_notification_message(include_details=False)

    if notification['has_data']:
        total = notification['summary']['total']
        success = notification['summary']['success']
        failed = notification['summary']['failed']
        print(f"✅ 签到完成，共处理 {total} 个站点")
        print(f"📊 成功: {success} 个，失败: {failed} 个")

        # 发送通知
        send(notification['title'], notification['content'])
    else:
        print("ℹ️ 今日暂无签到记录")
        send("PT签到提醒", "今日暂无签到记录，请检查配置")

    print("🎉 签到任务完成")


if __name__ == '__main__':
    main()
