import argparse
from pathlib import Path
from urllib.parse import urlparse

import yaml

from ptsites.core import Executor, SignInError, TaskManager
from ptsites.data.database import DatabaseManager
from ptsites.utils.cookie_cloud import CookieCloud
from ptsites.utils import logger, send_checkin_report, setup_logger


def main():
    parser = argparse.ArgumentParser(description="PT 自动签到脚本")
    parser.add_argument(
        "-f", "--file", type=str, default="config.yml", help="配置文件的路径"
    )
    args = parser.parse_args()
    config_path = Path(args.file)

    if not config_path.is_file():
        logger.error(f"配置文件不存在: {config_path}")
        return

    data_path = config_path.parent / "data"
    data_path.mkdir(exist_ok=True)
    setup_logger(data_path)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    db_manager = DatabaseManager(data_path / "data.db")
    task_manager = TaskManager(config)

    tasks = task_manager.build_tasks()
    if not tasks:
        logger.info("没有需要执行的签到任务。")
        return

    executor = Executor(config, db_manager)

    cookie_cloud_client = None
    cookie_cloud_config = config.get("cookie_cloud")
    if cookie_cloud_config:
        cookie_cloud_client = CookieCloud(
            cookie_cloud_config["url"],
            cookie_cloud_config["uuid"],
            cookie_cloud_config["password"],
            data_path=data_path,
        )

    results = []
    logger.info(f"开始为 {len(tasks)} 个站点执行签到任务...")

    for entry in tasks:
        site_name = entry["site_name"]

        if db_manager.has_signed_in_today(site_name):
            results.append(
                {"site_name": site_name, "status": "今日已签到", "details": "跳过"}
            )
            continue

        cookie = None
        source = "配置"
        use_cookie_cloud = entry.get("use_cookie_cloud", False)

        if use_cookie_cloud and cookie_cloud_client:
            cookie = db_manager.load_cookie(site_name)
            source = "数据库"
            if cookie is None:
                try:
                    domain = urlparse(entry["url"]).netloc
                    cookie = cookie_cloud_client.get_cookies(domain=domain)
                    source = "云端"
                    if cookie:
                        db_manager.save_cookie(site_name, cookie)
                except (ValueError, AttributeError):
                    logger.warning(
                        f"无法为站点 {site_name} 获取 URL，无法从 CookieCloud 获取 cookie。"
                    )

        if not cookie:
            cookie = entry.get("cookie")

        if not cookie:
            results.append(
                {
                    "site_name": site_name,
                    "status": "失败",
                    "details": "无法获取Cookie",
                }
            )
            continue

        entry["cookie"] = cookie

        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = executor.execute(entry)
                logger.info(f"站点 {site_name} 使用 {source} Cookie 签到成功。")
                results.append({"site_name": site_name, **result})
                break
            except SignInError as e:
                logger.warning(f"站点 {site_name} 第 {attempt + 1} 次尝试签到失败: {e}")
                if (
                    attempt < max_retries - 1
                    and use_cookie_cloud
                    and cookie_cloud_client
                ):
                    logger.info(f"尝试从云端强制获取 {site_name} 的新 Cookie...")
                    try:
                        domain = urlparse(entry["url"]).netloc
                        new_cookie = cookie_cloud_client.get_cookies(
                            domain=domain
                        )
                        if new_cookie:
                            logger.success(
                                f"成功从云端获取到 {site_name} 的新 Cookie。"
                            )
                            db_manager.save_cookie(site_name, new_cookie)
                            entry["cookie"] = new_cookie
                            source = "云端"
                            continue
                        else:
                            logger.error(f"无法从云端获取 {site_name} 的新 Cookie。")
                            break
                    except (ValueError, AttributeError):
                        logger.warning(
                            f"无法为站点 {site_name} 获取 URL，"
                            "无法从 CookieCloud 获取 cookie。"
                        )
                        break
                elif attempt >= max_retries - 1:
                    results.append(
                        {
                            "site_name": site_name,
                            "status": "失败",
                            "details": str(e),
                        }
                    )

    logger.info("所有签到任务执行完毕。")
    send_checkin_report(results, config)


if __name__ == "__main__":
    main()
