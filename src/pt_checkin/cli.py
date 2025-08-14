#!/usr/bin/env python3
"""
PT签到工具 - 简化版CLI
"""
import click
from loguru import logger
from .core.config_manager import ConfigManager


@click.group()
@click.option('-c', '--config', default='config.yml', help='配置文件路径')
@click.option('-v', '--verbose', is_flag=True, help='详细日志输出')
@click.pass_context
def cli(ctx, config: str, verbose: bool):
    """PT站点自动签到工具"""
    # 设置日志级别
    logger.remove()  # 移除默认处理器
    if verbose:
        logger.add(lambda msg: print(msg, end=''), level="DEBUG")
    else:
        logger.add(lambda msg: print(msg, end=''), level="INFO")

    # 初始化配置管理器
    try:
        config_manager = ConfigManager(config)
        ctx.ensure_object(dict)
        ctx.obj['config_manager'] = config_manager
        logger.info("程序初始化完成")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        ctx.exit(1)


# ==================== 核心命令 ====================

@cli.command()
@click.option('--site', '-s', help='仅签到指定站点')
@click.option('--force', is_flag=True, help='强制重新签到')
@click.option('--dry-run', is_flag=True, help='模拟运行')
@click.pass_context
def run(ctx, site: str, force: bool, dry_run: bool):
    """执行签到任务"""
    config_manager = ctx.obj['config_manager']
    
    if dry_run:
        logger.info("模拟运行模式，不会实际执行签到")
    
    # 创建调度器并执行
    from .core.scheduler import TaskScheduler
    scheduler = TaskScheduler(config_manager)
    
    # 设置强制选项
    force_options = {}
    if force:
        force_options['force_all'] = True
    if site:
        force_options['force_sites'] = [site]
    
    try:
        if dry_run:
            logger.info("模拟运行完成")
        else:
            scheduler.run_once(force_options)
    except Exception as e:
        logger.error(f"签到任务执行失败: {e}")
        ctx.exit(1)


# ==================== 测试命令 ====================

@cli.command()
@click.pass_context
def test(ctx):
    """测试配置文件"""
    config_manager = ctx.obj['config_manager']
    
    logger.info("=== 配置文件测试 ===")
    
    # 测试站点配置
    sites = config_manager.get_sites()
    logger.info(f"配置的站点数量: {len(sites)}")
    
    for site_name in sites.keys():
        logger.info(f"  - {site_name}")
    
    # 测试百度OCR配置
    baidu_ocr = config_manager.get_baidu_ocr_config()
    if baidu_ocr and baidu_ocr.get('app_id'):
        logger.info("百度OCR配置: 已配置")
    else:
        logger.info("百度OCR配置: 未配置")
    
    logger.info("配置文件测试完成")


@cli.command()
@click.argument('site_name')
@click.option('--debug', is_flag=True, help='启用调试模式')
@click.pass_context
def test_site(ctx, site_name: str, debug: bool):
    """测试单个站点"""
    config_manager = ctx.obj['config_manager']
    
    if debug:
        logger.debug("启用调试模式")
    
    # 检查站点配置
    sites = config_manager.get_sites()
    if site_name not in sites:
        logger.error(f"站点 {site_name} 未在配置文件中找到")
        ctx.exit(1)
    
    logger.info(f"测试站点 {site_name} 签到...")
    
    if debug:
        site_config = sites[site_name]
        logger.debug(f"站点配置: {site_config}")
    
    # 创建调度器并执行单站点测试
    from .core.scheduler import TaskScheduler
    scheduler = TaskScheduler(config_manager)
    
    # 临时修改配置只包含指定站点
    original_sites = config_manager.config['sites']
    config_manager.config['sites'] = {site_name: sites[site_name]}
    
    try:
        scheduler.run_once()
    finally:
        # 恢复原始配置
        config_manager.config['sites'] = original_sites


# ==================== 状态命令 ====================

@cli.command()
@click.option('--clear', is_flag=True, help='清除今日签到状态')
@click.option('--clear-site', help='清除指定站点状态')
@click.option('--show-failed', is_flag=True, help='显示失败统计')
@click.pass_context
def status(ctx, clear: bool, clear_site: str, show_failed: bool):
    """查看和管理签到状态"""
    from .core.signin_status import SignInStatusManager
    
    status_manager = SignInStatusManager()
    
    if clear:
        status_manager.clear_today_status()
        logger.info("已清除今日所有签到状态")
        return
    
    if clear_site:
        status_manager.clear_site_status(clear_site)
        logger.info(f"已清除站点 {clear_site} 的今日签到状态")
        return
    
    # 显示状态
    logger.info("=== 今日签到状态 ===")

    summary = status_manager.get_today_summary()
    if summary['total'] == 0:
        logger.info("今日暂无签到记录")
        return

    for site_name, status_info in summary['sites'].items():
        status_text = "✅ 成功" if status_info['status'] == 'success' else "❌ 失败"
        message = status_info.get('message', '')
        time_str = status_info.get('time', '')
        logger.info(f"  {site_name}: {status_text} - {message} ({time_str})")
    
    if show_failed:
        logger.info("\n=== 失败次数统计 ===")
        failed_counts = status_manager.get_all_failed_counts()
        if failed_counts:
            for site_name, count in failed_counts.items():
                if count > 0:
                    logger.info(f"  {site_name}: {count} 次")
        else:
            logger.info("暂无失败记录")


# ==================== 通知命令 ====================

@cli.command()
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text', help='输出格式')
@click.option('--title-only', is_flag=True, help='仅返回标题')
@click.option('--detailed', '-d', is_flag=True, help='显示详细信息（包含消息和详情）')
@click.pass_context
def get_notification(ctx, format: str, title_only: bool, detailed: bool):
    """获取最新签到结果通知消息"""
    # 使用便捷函数获取通知消息
    notification = get_notification_message(include_details=detailed)

    if not notification['has_data']:
        if format == 'json':
            import json
            result = {'title': '', 'content': '', 'has_data': False}
            print(json.dumps(result, ensure_ascii=False))
        else:
            print("")  # 空输出表示无数据
        return

    if title_only:
        print(notification['title'])
        return

    if format == 'json':
        import json
        result = {
            'title': notification['title'],
            'content': notification['content'],
            'has_data': True,
            'summary': notification['summary']
        }
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"标题: {notification['title']}")
        print(f"内容:\n{notification['content']}")


# ==================== 调试命令 ====================

@cli.command()
@click.option('--site', '-s', help='调试指定站点')
@click.option('--show-config', is_flag=True, help='显示配置信息')
@click.pass_context
def debug(ctx, site: str, show_config: bool):
    """调试模式"""
    config_manager = ctx.obj['config_manager']

    logger.info("=== 调试信息 ===")

    if show_config:
        logger.info("完整配置信息:")
        import json
        config_str = json.dumps(config_manager.config, indent=2, ensure_ascii=False)
        # 隐藏敏感信息
        config_str = config_str.replace('"cookie":', '"cookie": "[HIDDEN]",')
        logger.info(config_str)
        return

    # 显示站点概览
    sites = config_manager.get_sites()
    logger.info(f"配置的站点数量: {len(sites)}")

    if site:
        if site in sites:
            logger.info(f"站点 {site} 配置:")
            site_config = sites[site]
            for key, value in site_config.items():
                if key == 'cookie':
                    logger.info(f"  {key}: [HIDDEN]")
                else:
                    logger.info(f"  {key}: {value}")
        else:
            logger.error(f"站点 {site} 未找到")
    else:
        logger.info("所有站点:")
        for site_name in sites.keys():
            logger.info(f"  - {site_name}")


# ==================== 便捷函数 ====================

def run_signin(
    config_file: str = 'config.yml',
    force: bool = False,
    site: str | None = None
) -> dict:
    """
    便捷的签到执行函数，供外部脚本调用

    Args:
        config_file: 配置文件路径
        force: 是否强制重新签到
        site: 指定站点名称

    Returns:
        dict: 包含执行结果的字典
    """
    # 设置日志级别为INFO，不输出DEBUG信息
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), level="INFO")

    try:
        # 初始化配置管理器
        config_manager = ConfigManager(config_file)

        # 创建调度器
        from .core.scheduler import TaskScheduler
        scheduler = TaskScheduler(config_manager)

        # 设置强制选项
        force_options = {}
        if force:
            force_options['force_all'] = True
        if site:
            force_options['force_site'] = site

        # 执行签到
        scheduler.run_once(force_options)

        # 获取结果
        from .core.signin_status import SignInStatusManager
        status_manager = SignInStatusManager()
        summary = status_manager.get_today_summary()

        return {
            'success': True,
            'summary': summary,
            'error': None
        }

    except Exception as e:
        logger.error(f"签到执行失败: {e}")
        return {
            'success': False,
            'summary': None,
            'error': str(e)
        }


def get_notification_message(include_details: bool = False) -> dict:
    """
    获取通知消息的便捷函数

    Args:
        include_details: 是否包含详细信息（默认False，仅显示基本状态）

    Returns:
        dict: 包含通知信息的字典
    """
    try:
        from .core.signin_status import SignInStatusManager

        status_manager = SignInStatusManager()
        summary = status_manager.get_today_summary()

        if summary['total'] == 0:
            return {
                'has_data': False,
                'title': '',
                'content': '',
                'summary': summary
            }

        # 构建通知内容
        success_sites = []
        failed_sites = []

        for site_name, site_info in summary['sites'].items():
            if site_info['status'] == 'success':
                result_msg = site_info.get('result', '成功')
                site_line = f"✅ {site_name}: {result_msg}"

                # 如果需要详细信息，添加消息和详情
                if include_details:
                    messages = site_info.get('messages', '')
                    details = site_info.get('details', '')

                    if messages:
                        site_line += f"\n    📨 消息: {messages[:100]}..."

                    if details:
                        # 处理详情信息，提取关键信息
                        if isinstance(details, dict):
                            detail_parts = []
                            if details.get('points'):
                                detail_parts.append(f"魔力值: {details['points']}")
                            if details.get('share_ratio'):
                                detail_parts.append(f"分享率: {details['share_ratio']}")
                            if details.get('uploaded'):
                                detail_parts.append(f"上传: {details['uploaded']}")
                            if details.get('downloaded'):
                                detail_parts.append(f"下载: {details['downloaded']}")
                            if detail_parts:
                                site_line += f"\n    📈 详情: {' | '.join(detail_parts)}"
                        else:
                            details_str = str(details)[:100]
                            site_line += f"\n    📈 详情: {details_str}..."

                success_sites.append(site_line)
            else:
                reason = site_info.get('reason', '失败')
                site_line = f"❌ {site_name}: {reason}"

                # 失败站点也可以显示详细的失败原因
                if include_details and len(reason) > 50:
                    # 如果失败原因很长，在详细模式下显示完整信息
                    site_line = f"❌ {site_name}: {reason[:50]}...\n    详细原因: {reason}"

                failed_sites.append(site_line)

        # 生成标题
        if summary['failed'] == 0:
            title = f"PT签到成功 ({summary['success']}/{summary['total']})"
        else:
            title = f"PT签到完成 ({summary['success']}/{summary['total']})"

        # 生成完整内容
        content_lines = [
            "PT站点签到完成",
            "",
            "📊 结果统计:",
            f"• 总计: {summary['total']} 个站点",
            f"• 成功: {summary['success']} 个",
            f"• 失败: {summary['failed']} 个"
        ]

        if success_sites:
            content_lines.extend(["", "✅ 成功站点:"] + success_sites)

        if failed_sites:
            content_lines.extend(["", "❌ 失败站点:"] + failed_sites)

        content = "\n".join(content_lines)

        return {
            'has_data': True,
            'title': title,
            'content': content,
            'summary': summary
        }

    except Exception as e:
        logger.error(f"获取通知消息失败: {e}")
        return {
            'has_data': False,
            'title': '',
            'content': '',
            'summary': None,
            'error': str(e)
        }


def main():
    """主入口函数"""
    cli()


if __name__ == '__main__':
    main()
