from dependency_injector import containers, providers

from ptsites.data.database import DatabaseManager
from ptsites.utils.cookie_cloud import CookieCloud


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    db_manager = providers.Singleton(
        DatabaseManager,
        db_path=config.data_path
    )

    cookie_cloud_client = providers.Singleton(
        CookieCloud,
        url=config.cookie_cloud.url,
        uuid=config.cookie_cloud.uuid,
        password=config.cookie_cloud.password,
        data_path=config.data_path.provided_for(DatabaseManager)
    )

    task_manager = providers.Factory(
        'ptsites.core.task_manager.TaskManager',
        config=config
    )

    executor = providers.Factory(
        'ptsites.core.executor.Executor',
        config=config,
        db_manager=db_manager,
        cookie_cloud_client=cookie_cloud_client
    )