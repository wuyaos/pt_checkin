"""任务调度器"""
from datetime import datetime

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

    def run_sign_in_task(self, force_options: dict = None) -> None:
        """执行签到任务"""
        logger.info("任务调度 - 开始执行: 签到任务")
        start_time = datetime.now()

        if force_options is None:
            force_options = {'force_all': False, 'force_site': None}

        try:
            # 动态导入避免循环导入
            from .executor import create_sign_in_entries
            # 移除notify导入，使用内置日志记录

            # 准备配置
            config = self.config_manager.prepare_config_for_executor()
            sites_config = self.config_manager.get_sites()

            if not sites_config:
                logger.warning("任务调度 - 配置检查: 未配置任何站点，跳过签到任务")
                return

            # 创建签到条目
            entries = create_sign_in_entries(sites_config, config)
            if not entries:
                logger.warning("任务调度 - 条目创建: 未创建任何签到条目")
                return

            logger.info(f"任务调度 - 条目创建: 成功创建 {len(entries)} 个签到条目")

            # 过滤今日条目和已签到条目
            date_now = str(datetime.now().date())
            valid_entries = []
            skipped_entries = []

            # 获取失败次数限制配置
            max_failed_attempts = self.config_manager.get_max_failed_attempts()
            retry_interval = self.config_manager.get_failed_retry_interval()

            for entry in entries:
                if date_now not in entry['title']:
                    continue

                site_name = entry['site_name']

                # 如果指定了特定站点，只处理指定的站点
                force_sites = force_options.get('force_sites', [])
                if force_sites and site_name not in force_sites:
                    continue

                # 检查是否需要强制签到
                force_sites = force_options.get('force_sites', [])
                should_force = force_options.get('force_all', False)

                # 检查是否已签到
                if not should_force and self.status_manager.is_signed_today(site_name):
                    status = self.status_manager.get_site_status(site_name)
                    result = status.get('result', '已签到')
                    skip_msg = f"{site_name} - 跳过签到: 今日已签到 ({result})"
                    logger.info(skip_msg)
                    skipped_entries.append({
                        'site': site_name,
                        'reason': f"已签到 - {status.get('result', '')}",
                        'time': status.get('time', ''),
                        'type': 'signed'
                    })
                    continue

                # 检查失败次数限制
                if not should_force:
                    skip_result = self.status_manager.should_skip_due_to_failures(
                        site_name, max_failed_attempts, retry_interval
                    )
                    should_skip, skip_reason = skip_result
                    if should_skip:
                        failed_count = self.status_manager.get_failed_count(site_name)
                        logger.warning(f"{site_name} - 跳过签到: {skip_reason}")
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
                    self.status_manager.clear_site_status(site_name, True)
                    if force_options.get('force_all'):
                        logger.info(f"{site_name} - 强制签到: 清除今日状态")

                valid_entries.append(entry)

            if not valid_entries:
                if skipped_entries:
                    skip_count = len(skipped_entries)
                    logger.info(f"任务调度 - 执行结果: 所有站点今日已签到，跳过 {skip_count} 个站点")
                else:
                    logger.info("任务调度 - 执行结果: 没有需要签到的条目")
                return

            logger.info(f"任务调度 - 开始执行: {len(valid_entries)} 个站点签到")

            # 执行签到（顺序执行）
            success_count = 0
            failed_count = 0
            success_results = []
            failed_results = []

            # 顺序执行每个站点的签到
            for entry in valid_entries:
                try:
                    self._sign_in_with_error_handling(entry, config)
                    if entry.failed:
                        failed_count += 1
                        failed_results.append({
                            'site': entry['site_name'],
                            'reason': entry.reason
                        })
                        # 记录签到失败状态
                        site_name = entry['site_name']
                        self.status_manager.record_signin_failed(site_name, entry.reason)
                        logger.error(f"{site_name} - 签到失败: {entry.reason}")
                    else:
                        success_count += 1
                        success_results.append({
                            'site': entry['site_name'],
                            'result': entry.get('result', '签到成功'),
                            'messages': entry.get('messages', ''),
                            'details': entry.get('details', ''),
                            'messages_status': entry.get('messages_status', 'success'),
                            'details_status': entry.get('details_status', 'success'),
                            'messages_error': entry.get('messages_error', ''),
                            'details_error': entry.get('details_error', ''),
                            'signin_type': entry.get('signin_type', '签到成功')
                        })
                        # 记录签到成功状态
                        self.status_manager.record_signin_success(
                            entry['site_name'],
                            entry.get('result', '签到成功'),
                            entry.get('messages', ''),
                            entry.get('details', ''),
                            entry.get('signin_type', '签到成功')
                        )
                        site_name = entry['site_name']
                        result = entry.get('result', '')
                        logger.info(f"{site_name} - 签到成功: {result}")

                        # 记录消息和详情获取状态
                        if entry.get('messages_status') == 'failed':
                            msg_error = entry.get('messages_error', '')
                            logger.warning(f"{site_name} - 消息获取失败: {msg_error}")
                        if entry.get('details_status') == 'failed':
                            detail_error = entry.get('details_error', '')
                            logger.warning(f"{site_name} - 详情获取失败: {detail_error}")
                except Exception as e:
                    failed_count += 1
                    failed_results.append({
                        'site': entry['site_name'],
                        'reason': f"签到异常: {e}"
                    })
                    # 记录签到异常状态
                    site_name = entry['site_name']
                    error_msg = f"签到异常: {e}"
                    self.status_manager.record_signin_failed(site_name, error_msg)
                    logger.exception(f"{site_name} - 签到异常: {e}")

            # 统计结果
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 构建详细的通知内容
            notification_lines = [
                "📊 签到任务完成",
                f"总计: {len(valid_entries)} 个站点 | 成功: {success_count} 个 | 失败: {failed_count} 个",
                f"⏱️ 耗时: {duration:.2f} 秒",
                ""
            ]

            # 添加成功站点详情
            if success_results:
                notification_lines.append("✅ 签到成功:")
                for result in success_results:
                    # 固定使用6个空格对齐
                    alignment_spaces = "      "

                    # 站点名：具体状态
                    signin_type = result.get('signin_type', '签到成功')
                    site_status = f"{result['site']}：{signin_type}"
                    notification_lines.append(site_status)

                    # 签到消息
                    if result['result']:
                        msg_line = f"{alignment_spaces}签到消息：{result['result']}"
                        notification_lines.append(msg_line)

                    # 消息获取状态（只显示失败的情况）
                    if result.get('messages_status') == 'failed':
                        msg_error = result.get('messages_error', '')
                        error_line = f"{alignment_spaces}摘要：消息获取失败 - {msg_error}"
                        notification_lines.append(error_line)

                    # 详情获取状态和内容（只显示失败或成功时的账户信息）
                    if result.get('details_status') == 'failed':
                        detail_error = result.get('details_error', '')
                        detail_line = f"{alignment_spaces}摘要：详情获取失败 - {detail_error}"
                        notification_lines.append(detail_line)
                    elif result['details']:
                        # 格式化详情信息为账户信息
                        if isinstance(result['details'], dict):
                            detail_parts = []
                            for key, value in result['details'].items():
                                if key == 'points':
                                    detail_parts.append(f"G值: {value}")
                                elif key == 'share_ratio':
                                    detail_parts.append(f"分享率: {value}")
                                elif key == 'uploaded':
                                    detail_parts.append(f"上传: {value}")
                                elif key == 'downloaded':
                                    detail_parts.append(f"下载: {value}")
                            if detail_parts:
                                account_info = ' | '.join(detail_parts)
                                account_line = f"{alignment_spaces}账户：{account_info}"
                                notification_lines.append(account_line)

                    notification_lines.append("")  # 空行分隔每个站点

            # 添加失败站点详情
            if failed_results:
                notification_lines.append("❌ 签到失败:")
                for result in failed_results:
                    # 固定使用6个空格对齐
                    alignment_spaces = "      "

                    # 站点名：签到失败
                    notification_lines.append(f"{result['site']}：签到失败")
                    # 摘要（失败原因）
                    reason_line = f"{alignment_spaces}摘要：{result['reason']}"
                    notification_lines.append(reason_line)
                    notification_lines.append("")  # 空行分隔每个站点

            # 添加跳过的站点信息
            if skipped_entries:
                # 分类显示跳过的站点
                signed_skipped = [s for s in skipped_entries if s.get('type') == 'signed']
                failed_skipped = [s for s in skipped_entries
                                  if s.get('type') == 'failed_too_much']

                if signed_skipped:
                    notification_lines.append("⏭️ 跳过已签到:")
                    for skipped in signed_skipped:
                        site = skipped['site']
                        reason = skipped['reason']
                        time_str = skipped['time']
                        skip_line = f"  • {site}: {reason} ({time_str})"
                        notification_lines.append(skip_line)
                    notification_lines.append("")

                if failed_skipped:
                    notification_lines.append("🚫 跳过失败过多:")
                    for skipped in failed_skipped:
                        failed_count = skipped.get('failed_count', 0)
                        site = skipped['site']
                        reason = skipped['reason']
                        fail_line = f"  • {site}: {reason} (失败{failed_count}次)"
                        notification_lines.append(fail_line)
                    notification_lines.append("")

            # 添加时间信息
            time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
            time_line = f"🕐 执行时间: {time_str}"
            notification_lines.append(time_line)

            result_message = "\n".join(notification_lines)

            skip_count = len(skipped_entries)
            stats = f"成功 {success_count} 个，失败 {failed_count} 个，跳过 {skip_count} 个"
            logger.info(f"任务调度 - 执行完成: {stats}，耗时 {duration:.2f} 秒")

            # 记录签到结果到日志
            logger.info(f"任务调度 - 结果摘要:\n{result_message}")

            # 清理旧记录
            self.status_manager.cleanup_old_records()

        except Exception as e:
            logger.exception(f"任务调度 - 执行异常: {e}")

    def _sign_in_with_error_handling(self, entry: SignInEntry, config: dict) -> None:
        """带错误处理的签到"""
        try:
            from .executor import sign_in
            sign_in(entry, config)
        except Exception as e:
            entry.fail(f"签到异常: {e}")
            logger.exception(f"{entry['site_name']} - 签到异常: {e}")

    def run_once(self, force_options: dict = None) -> None:
        """立即执行一次签到任务"""
        logger.info("任务调度 - 立即执行: 签到任务")
        self.run_sign_in_task(force_options)