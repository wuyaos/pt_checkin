"""
任务调度器
负责定时执行签到任务
"""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List

import schedule
from loguru import logger

from .config_manager import ConfigManager
from .entry import SignInEntry
from .signin_status import SignInStatusManager


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        # 状态文件保存到配置文件同级目录
        status_file = config_manager.config_dir / 'signin_status.json'
        self.status_manager = SignInStatusManager(str(status_file))
        self.running = False
    
    def setup_schedule(self) -> None:
        """设置调度任务"""
        schedule_time = self.config_manager.get_schedule_time()
        schedule.every().day.at(schedule_time).do(self.run_sign_in_task)
        logger.info(f"已设置每日 {schedule_time} 执行签到任务")
    
    def run_sign_in_task(self, force_options: dict = None) -> None:
        """执行签到任务"""
        logger.info("开始执行签到任务")
        start_time = datetime.now()

        if force_options is None:
            force_options = {'force_all': False, 'force_site': None}

        try:
            # 动态导入避免循环导入
            from .executor import create_sign_in_entries, sign_in
            # 移除notify导入，使用内置日志记录

            # 准备配置
            config = self.config_manager.prepare_config_for_executor()
            sites_config = self.config_manager.get_sites()

            if not sites_config:
                logger.warning("未配置任何站点，跳过签到任务")
                return

            # 创建签到条目
            entries = create_sign_in_entries(sites_config, config)
            if not entries:
                logger.warning("未创建任何签到条目")
                return
            
            logger.info(f"创建了 {len(entries)} 个签到条目")
            
            # 过滤今日条目和已签到条目
            date_now = str(datetime.now().date())
            valid_entries = []
            skipped_entries = []

            # 获取失败次数限制配置
            max_failed_attempts = self.config_manager.get_max_failed_attempts()
            retry_interval = self.config_manager.get_failed_retry_interval()

            for entry in entries:
                if date_now not in entry['title']:
                    logger.debug(f"{entry['title']} 不是今日条目，跳过")
                    continue

                site_name = entry['site_name']

                # 如果指定了特定站点，只处理指定的站点
                force_sites = force_options.get('force_sites', [])
                if force_sites and site_name not in force_sites:
                    logger.debug(f"跳过未指定站点: {site_name}")
                    continue

                # 检查是否需要强制签到
                force_sites = force_options.get('force_sites', [])
                should_force = force_options.get('force_all', False)

                # 检查是否已签到
                if not should_force and self.status_manager.is_signed_today(site_name):
                    status = self.status_manager.get_site_status(site_name)
                    logger.info(f"跳过已签到站点: {site_name} - {status.get('result', '已签到')} ({status.get('time', '')})")
                    skipped_entries.append({
                        'site': site_name,
                        'reason': f"已签到 - {status.get('result', '')}",
                        'time': status.get('time', ''),
                        'type': 'signed'
                    })
                    continue

                # 检查失败次数限制
                if not should_force:
                    should_skip, skip_reason = self.status_manager.should_skip_due_to_failures(
                        site_name, max_failed_attempts, retry_interval
                    )
                    if should_skip:
                        failed_count = self.status_manager.get_failed_count(site_name)
                        logger.warning(f"跳过失败过多站点: {site_name} - {skip_reason}")
                        skipped_entries.append({
                            'site': site_name,
                            'reason': skip_reason,
                            'time': '',
                            'type': 'failed_too_much',
                            'failed_count': failed_count
                        })
                        continue

                # 如果是强制签到，清除之前的状态（但保留失败次数）
                if should_force:
                    self.status_manager.clear_site_status(site_name, keep_failed_count=True)
                    if force_options.get('force_all'):
                        logger.info(f"强制重新签到所有站点，包括: {site_name}")

                valid_entries.append(entry)

            if not valid_entries:
                if skipped_entries:
                    logger.info(f"所有站点今日已签到，跳过 {len(skipped_entries)} 个站点")
                    # 显示跳过的站点摘要
                    for skipped in skipped_entries:
                        logger.info(f"  - {skipped['site']}: {skipped['reason']}")
                else:
                    logger.info("没有需要签到的条目")
                return
            
            logger.info(f"开始签到 {len(valid_entries)} 个站点")
            
            # 执行签到
            max_workers = self.config_manager.get_max_workers()
            success_count = 0
            failed_count = 0
            success_results = []
            failed_results = []

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for entry in valid_entries:
                    future = executor.submit(self._sign_in_with_error_handling, entry, config)
                    futures.append((entry, future))

                # 等待所有任务完成
                for entry, future in futures:
                    try:
                        future.result()
                        if entry.failed:
                            failed_count += 1
                            failed_results.append({
                                'site': entry['site_name'],
                                'reason': entry.reason
                            })
                            # 记录签到失败状态
                            self.status_manager.record_signin_failed(entry['site_name'], entry.reason)
                            logger.error(f"签到失败: {entry['title']} - {entry.reason}")
                        else:
                            success_count += 1
                            success_results.append({
                                'site': entry['site_name'],
                                'result': entry.get('result', '签到成功'),
                                'messages': entry.get('messages', ''),
                                'details': entry.get('details', '')
                            })
                            # 记录签到成功状态
                            self.status_manager.record_signin_success(
                                entry['site_name'],
                                entry.get('result', '签到成功'),
                                entry.get('messages', ''),
                                entry.get('details', '')
                            )
                            logger.info(f"签到成功: {entry['title']} - {entry.get('result', '')}")
                    except Exception as e:
                        failed_count += 1
                        failed_results.append({
                            'site': entry['site_name'],
                            'reason': f"签到异常: {e}"
                        })
                        # 记录签到异常状态
                        self.status_manager.record_signin_failed(entry['site_name'], f"签到异常: {e}")
                        logger.exception(f"签到异常: {entry['title']} - {e}")
            
            # 统计结果
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 构建详细的通知内容
            notification_lines = [
                f"📊 签到任务完成",
                f"总计: {len(valid_entries)} 个站点 | 成功: {success_count} 个 | 失败: {failed_count} 个",
                f"⏱️ 耗时: {duration:.2f} 秒",
                ""
            ]

            # 添加成功站点详情
            if success_results:
                notification_lines.append("✅ 签到成功:")
                for result in success_results:
                    site_info = f"  • {result['site']}: {result['result']}"
                    notification_lines.append(site_info)

                    # 如果有消息，添加消息信息
                    if result['messages']:
                        notification_lines.append(f"    📨 消息: {result['messages'][:100]}...")

                    # 如果有详情，添加详情信息
                    if result['details']:
                        details_str = str(result['details'])[:100]
                        notification_lines.append(f"    📈 详情: {details_str}...")

                notification_lines.append("")

            # 添加失败站点详情
            if failed_results:
                notification_lines.append("❌ 签到失败:")
                for result in failed_results:
                    notification_lines.append(f"  • {result['site']}: {result['reason'][:100]}...")
                notification_lines.append("")

            # 添加跳过的站点信息
            if skipped_entries:
                # 分类显示跳过的站点
                signed_skipped = [s for s in skipped_entries if s.get('type') == 'signed']
                failed_skipped = [s for s in skipped_entries if s.get('type') == 'failed_too_much']

                if signed_skipped:
                    notification_lines.append("⏭️ 跳过已签到:")
                    for skipped in signed_skipped:
                        notification_lines.append(f"  • {skipped['site']}: {skipped['reason']} ({skipped['time']})")
                    notification_lines.append("")

                if failed_skipped:
                    notification_lines.append("🚫 跳过失败过多:")
                    for skipped in failed_skipped:
                        failed_count = skipped.get('failed_count', 0)
                        notification_lines.append(f"  • {skipped['site']}: {skipped['reason']} (失败{failed_count}次)")
                    notification_lines.append("")

            # 添加时间信息
            notification_lines.append(f"🕐 执行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            result_message = "\n".join(notification_lines)

            logger.info(f"签到任务完成 - 成功: {success_count}, 失败: {failed_count}, 跳过: {len(skipped_entries)}, 耗时: {duration:.2f}秒")

            # 记录签到结果到日志
            logger.info(f"签到结果摘要:\n{result_message}")

            # 清理旧记录
            self.status_manager.cleanup_old_records()
            
        except Exception as e:
            error_msg = f"签到任务执行异常: {e}"
            logger.exception(error_msg)
            # 记录错误到日志
            logger.error(f"签到任务执行失败: {error_msg}")
    
    def _sign_in_with_error_handling(self, entry: SignInEntry, config: dict) -> None:
        """带错误处理的签到"""
        try:
            from .executor import sign_in
            sign_in(entry, config)
        except Exception as e:
            entry.fail(f"签到异常: {e}")
            logger.exception(f"站点 {entry['site_name']} 签到异常: {e}")
    
    def run_once(self, force_options: dict = None) -> None:
        """立即执行一次签到任务"""
        logger.info("立即执行签到任务")
        self.run_sign_in_task(force_options)
    
    def start(self) -> None:
        """启动调度器"""
        self.running = True
        self.setup_schedule()
        logger.info("任务调度器已启动")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """停止调度器"""
        self.running = False
        schedule.clear()
        logger.info("任务调度器已停止")
