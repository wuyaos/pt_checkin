import argparse
from pathlib import Path
import yaml


from ptsites.core.container import Container
from ptsites.utils import logger, send_checkin_report, setup_logger


def process_signin_tasks(
    tasks,
    container: Container,
):
    """
    处理所有签到任务
    """
    results = []
    logger.info(f"开始为 {len(tasks)} 个站点执行签到任务...")
    executor = container.executor()

    for entry in tasks:
        result = executor.execute_with_retry(entry)
        results.append(result)

    logger.info("所有签到任务执行完毕。")
    return results


def main():
    container = Container()
    container.wire(modules=[
        __name__,
        "ptsites.core.task_manager",
        "ptsites.core.executor",
    ])

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
        config_data = yaml.safe_load(f)
    container.config.from_dict(config_data)
    container.config.data_path.from_value(str(data_path / 'data.db'))

    task_manager = container.task_manager()

    tasks = task_manager.build_tasks()
    if not tasks:
        logger.info("没有需要执行的签到任务。")
        return

    results = process_signin_tasks(
        tasks, container
    )
    send_checkin_report(results, container.config())


if __name__ == "__main__":
    main()
