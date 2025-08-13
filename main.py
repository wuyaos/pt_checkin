#!/usr/bin/env python3
"""
PT站点自动签到工具
独立版本，移除FlexGet依赖
"""
import sys
import os
import pathlib
from typing import Optional

# 确保正确的导入路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import click
from loguru import logger


def setup_logging(verbose: bool = False) -> None:
    """设置日志"""
    logger.remove()  # 移除默认处理器
    
    # 控制台日志
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 文件日志
    logger.add(
        "logs/pt_signin_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="30 days",
        compression="zip"
    )


@click.group()
@click.option('--config', '-c', default='config.yml', help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细日志输出')
@click.pass_context
def cli(ctx, config: str, verbose: bool):
    """PT站点自动签到工具"""
    setup_logging(verbose)

    # 创建logs目录
    pathlib.Path('logs').mkdir(exist_ok=True)

    try:
        # 动态导入避免循环导入问题
        from core.config_manager import ConfigManager
        config_manager = ConfigManager(config)
        ctx.obj = {'config_manager': config_manager}
        logger.info("程序初始化完成")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)


@cli.command()
@click.option('--now', is_flag=True, help='立即执行一次签到后启动定时服务')
@click.pass_context
def run(ctx, now: bool):
    """启动定时签到服务"""
    from core.scheduler import TaskScheduler
    config_manager = ctx.obj['config_manager']
    scheduler = TaskScheduler(config_manager)

    if now:
        logger.info("立即执行一次签到任务...")
        scheduler.run_once()
        logger.info("立即签到完成，现在启动定时服务...")

    logger.info("启动定时签到服务...")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("服务已停止")


@cli.command()
@click.option('--site', '-s', help='仅签到指定站点')
@click.option('--dry-run', is_flag=True, help='模拟运行，不实际执行签到')
@click.option('--force', is_flag=True, help='强制重新签到所有站点（忽略今日已签到状态）')
@click.option('--force-site', help='强制重新签到指定站点（忽略今日已签到状态）')
@click.pass_context
def once(ctx, site: str, dry_run: bool, force: bool, force_site: str):
    """立即执行一次签到"""
    from core.scheduler import TaskScheduler
    from core.signin_status import SignInStatusManager
    config_manager = ctx.obj['config_manager']

    # 处理强制签到选项
    force_options = {
        'force_all': force,
        'force_site': force_site
    }

    if site:
        # 检查站点是否存在
        sites = config_manager.get_sites()
        if site not in sites:
            logger.error(f"站点 {site} 未在配置文件中找到")
            available_sites = list(sites.keys())
            if available_sites:
                logger.info(f"可用站点: {', '.join(available_sites)}")
            return

        # 创建单站点配置
        logger.info(f"仅签到站点: {site}")
        original_sites = config_manager.config['sites'].copy()
        config_manager.config['sites'] = {site: sites[site]}

    if dry_run:
        logger.info("模拟运行模式 - 不会实际执行签到")
        # 这里可以添加模拟逻辑
        return

    scheduler = TaskScheduler(config_manager)

    logger.info("立即执行签到任务...")
    scheduler.run_once(force_options=force_options)
    logger.info("签到任务执行完成")

    # 恢复原始配置
    if site:
        config_manager.config['sites'] = original_sites


@cli.command()
@click.pass_context
def test(ctx):
    """测试配置文件"""
    config_manager = ctx.obj['config_manager']
    
    logger.info("测试配置文件...")
    
    # 显示配置信息
    sites = config_manager.get_sites()
    logger.info(f"配置的站点数量: {len(sites)}")
    
    for site_name in sites.keys():
        logger.info(f"  - {site_name}")
    
    logger.info(f"User-Agent: {config_manager.get_user_agent()}")
    logger.info(f"最大工作线程: {config_manager.get_max_workers()}")
    logger.info(f"调度时间: {config_manager.get_schedule_time()}")
    
    # 测试百度OCR配置
    ocr_config = config_manager.get_baidu_ocr_config()
    if any(ocr_config.values()):
        logger.info("百度OCR配置: 已配置")
    else:
        logger.info("百度OCR配置: 未配置")
    
    logger.info("配置文件测试完成")


@cli.command()
@click.argument('site_name')
@click.option('--debug', is_flag=True, help='启用详细调试信息')
@click.pass_context
def test_site(ctx, site_name: str, debug: bool):
    """测试单个站点签到"""
    from core.scheduler import TaskScheduler
    config_manager = ctx.obj['config_manager']

    if debug:
        # 临时提升日志级别
        logger.remove()
        logger.add(
            sys.stdout,
            level="DEBUG",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        logger.debug("启用调试模式")

    sites = config_manager.get_sites()
    if site_name not in sites:
        logger.error(f"站点 {site_name} 未在配置文件中找到")
        available_sites = list(sites.keys())
        if available_sites:
            logger.info(f"可用站点: {', '.join(available_sites)}")
        return

    logger.info(f"测试站点 {site_name} 签到...")

    if debug:
        logger.debug(f"站点配置: {sites[site_name]}")

    # 创建单站点配置
    original_sites = config_manager.config['sites'].copy()
    config_manager.config['sites'] = {site_name: sites[site_name]}

    scheduler = TaskScheduler(config_manager)
    scheduler.run_once()

    # 恢复原始配置
    config_manager.config['sites'] = original_sites


@cli.command()
@click.option('--site', '-s', help='调试指定站点')
@click.option('--show-config', is_flag=True, help='显示完整配置信息')
@click.option('--show-cookies', is_flag=True, help='显示cookie信息（敏感信息会被遮蔽）')
@click.pass_context
def debug(ctx, site: str, show_config: bool, show_cookies: bool):
    """调试模式 - 显示详细信息但不执行签到"""
    config_manager = ctx.obj['config_manager']

    logger.info("=== 调试模式 ===")

    if show_config:
        logger.info("=== 完整配置信息 ===")
        config = config_manager.prepare_config_for_executor()
        for key, value in config.items():
            if key != 'sites':
                logger.info(f"{key}: {value}")

    sites = config_manager.get_sites()
    logger.info(f"配置的站点数量: {len(sites)}")

    if site:
        if site not in sites:
            logger.error(f"站点 {site} 未在配置文件中找到")
            logger.info(f"可用站点: {', '.join(sites.keys())}")
            return

        logger.info(f"=== 站点 {site} 详细信息 ===")
        site_config = sites[site]

        if isinstance(site_config, str):
            logger.info("配置类型: 简单cookie配置")
            if show_cookies:
                masked_cookie = site_config[:10] + "..." + site_config[-10:] if len(site_config) > 20 else "***"
                logger.info(f"Cookie: {masked_cookie}")
        elif isinstance(site_config, dict):
            logger.info("配置类型: 详细配置")
            for key, value in site_config.items():
                if key == 'cookie' and show_cookies:
                    masked_value = value[:10] + "..." + value[-10:] if len(str(value)) > 20 else "***"
                    logger.info(f"  {key}: {masked_value}")
                elif key != 'cookie':
                    logger.info(f"  {key}: {value}")
                elif not show_cookies:
                    logger.info(f"  {key}: *** (使用 --show-cookies 显示)")

        # 尝试导入站点类
        try:
            import importlib
            site_module = importlib.import_module(f'sites.{site.lower()}')
            site_class = getattr(site_module, 'MainClass')
            logger.info(f"站点类: {site_class.__name__}")
            logger.info(f"站点URL: {getattr(site_class, 'URL', '未定义')}")
            logger.info(f"成功正则: {getattr(site_class, 'SUCCEED_REGEX', '未定义')}")
        except Exception as e:
            logger.error(f"无法加载站点类: {e}")
            logger.debug(f"尝试导入模块: sites.{site.lower()}")

    else:
        logger.info("=== 所有站点概览 ===")
        for site_name in sites.keys():
            site_config = sites[site_name]
            config_type = "简单配置" if isinstance(site_config, str) else "详细配置"
            logger.info(f"  - {site_name}: {config_type}")

    logger.info("=== 调试完成 ===")


@cli.command()
@click.option('--clear', is_flag=True, help='清除今日所有签到状态')
@click.option('--clear-site', help='清除指定站点的今日签到状态')
@click.option('--reset-failed', help='重置指定站点的失败次数')
@click.option('--show-failed', is_flag=True, help='显示失败次数统计')
@click.pass_context
def status(ctx, clear: bool, clear_site: str, reset_failed: str, show_failed: bool):
    """查看或管理签到状态"""
    from core.signin_status import SignInStatusManager

    status_manager = SignInStatusManager()

    if clear:
        status_manager.clear_all_status()
        logger.info("已清除今日所有签到状态")
        return

    if clear_site:
        config_manager = ctx.obj['config_manager']
        sites = config_manager.get_sites()
        if clear_site not in sites:
            logger.error(f"站点 {clear_site} 未在配置文件中找到")
            return

        status_manager.clear_site_status(clear_site)
        logger.info(f"已清除站点 {clear_site} 的今日签到状态")
        return

    if reset_failed:
        config_manager = ctx.obj['config_manager']
        sites = config_manager.get_sites()
        if reset_failed not in sites:
            logger.error(f"站点 {reset_failed} 未在配置文件中找到")
            return

        status_manager.reset_failed_count(reset_failed)
        logger.info(f"已重置站点 {reset_failed} 的失败次数")
        return

    # 显示签到状态
    summary = status_manager.get_today_summary()
    config_manager = ctx.obj['config_manager']
    max_failed_attempts = config_manager.get_max_failed_attempts()

    logger.info("=== 今日签到状态 ===")
    logger.info(f"总计: {summary['total']} 个站点")
    logger.info(f"成功: {summary['success']} 个")
    logger.info(f"失败: {summary['failed']} 个")
    logger.info(f"失败次数限制: {max_failed_attempts} 次")

    if summary['sites']:
        logger.info("\n=== 详细状态 ===")
        for site_name, site_data in summary['sites'].items():
            status_text = site_data.get('status', 'unknown')
            time_text = site_data.get('time', '')
            failed_count = site_data.get('failed_count', 0)

            if status_text == 'success':
                result = site_data.get('result', '签到成功')
                logger.info(f"✅ {site_name}: {result} ({time_text})")
            else:
                reason = site_data.get('reason', '未知错误')
                failed_info = f" [失败{failed_count}次]" if failed_count > 0 else ""
                logger.info(f"❌ {site_name}: {reason} ({time_text}){failed_info}")

        # 显示失败次数统计
        if show_failed:
            logger.info("\n=== 失败次数统计 ===")
            failed_sites = [(name, data) for name, data in summary['sites'].items()
                          if data.get('failed_count', 0) > 0]

            if failed_sites:
                for site_name, site_data in failed_sites:
                    failed_count = site_data.get('failed_count', 0)
                    status_icon = "🚫" if failed_count >= max_failed_attempts else "⚠️"
                    logger.info(f"{status_icon} {site_name}: {failed_count} 次失败")
            else:
                logger.info("没有站点有失败记录")
    else:
        logger.info("今日尚未进行任何签到")


if __name__ == '__main__':
    cli()
