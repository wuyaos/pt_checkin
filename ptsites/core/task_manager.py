from __future__ import annotations

import importlib
import pathlib
import pkgutil
from typing import List

from dependency_injector.wiring import Provide, inject

from ..base.entry import SignInEntry
from ..base.sign_in import SignIn
from ..utils import logger


class TaskManager:
    @inject
    def __init__(self, config: dict = Provide[".container.Container.config"]):
        self.config = config
        self.sites_schema = self._build_sign_in_schema()

    def build_tasks(self) -> List[SignInEntry]:
        """
        Build a list of sign-in tasks based on the configuration.
        """
        tasks = []
        sites_config = self.config.get('sites', {})
        if not sites_config:
            logger.warning("配置文件中未找到任何站点配置。")
            return tasks

        for site_name, site_config in sites_config.items():
            if site_name not in self.sites_schema:
                logger.warning(f"站点 {site_name} 未被支持，已跳过。")
                continue

            schema = self.sites_schema[site_name]
            entry = SignInEntry(
                site_name=site_name,
                class_name=schema.get('class_name', site_name.capitalize()),
                url=site_config.get('url')
            )

            try:
                site_class = self._get_site_class(entry['class_name'])
                if issubclass(site_class, SignIn):
                    site_class.sign_in_build_entry(entry, site_config)
            except (AttributeError, ValueError) as e:
                raise ValueError(f"site: {entry['site_name']}, error: {e}")

            # Add global configs to entry
            entry['user_agent'] = self.config.get('user-agent')
            entry['cookie_backup'] = self.config.get('cookie_backup', True)
            entry['aipocr'] = self.config.get('aipocr', {})
            entry['use_cookie_cloud'] = site_config.get(
                'use_cookie_cloud', False
            )

            tasks.append(entry)
        return tasks

    def _build_sign_in_schema(self) -> dict:
        """
        Build a schema of all available sites from the sites directory.
        """
        sites_schema: dict = {}
        sites_path = (
            pathlib.PurePath(__file__).parent.parent / 'sites'
        )
        module_info = None
        try:
            for module_info in pkgutil.iter_modules([str(sites_path)]):
                site_class = self._get_site_class(module_info.name)
                if issubclass(site_class, SignIn):
                    sites_schema.update(site_class.sign_in_build_schema())
        except (AttributeError, ValueError) as e:
            site_name = module_info.name if module_info else 'Unknown'
            raise ValueError(f"site: {site_name}, error: {e}")
        return sites_schema

    @staticmethod
    def _get_site_class(class_name: str) -> type:
        """
        Dynamically import and return the site class.
        """
        try:
            module_path = f'ptsites.sites.{class_name.lower()}'
            site_module = importlib.import_module(module_path)
            return getattr(site_module, 'MainClass')
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not find site {class_name}: {e}")