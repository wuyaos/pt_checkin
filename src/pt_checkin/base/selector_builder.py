from __future__ import annotations

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from ..utils import net_utils


class SelectorConfig:
    """选择器配置类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    def merge(self, other_config: Dict[str, Any]) -> 'SelectorConfig':
        """合并配置"""
        merged = self.config.copy()
        net_utils.dict_merge(merged, other_config)
        return SelectorConfig(merged)


class SelectorBuilder(ABC):
    """选择器构建器抽象基类"""
    
    def __init__(self, base_selector: Optional[Dict[str, Any]] = None):
        self.base_selector = base_selector or {}
    
    @abstractmethod
    def build(self) -> Dict[str, Any]:
        """构建选择器"""
        pass
    
    def with_base(self, base_selector: Dict[str, Any]) -> 'SelectorBuilder':
        """设置基础选择器"""
        self.base_selector = base_selector
        return self
    
    def merge_selectors(self, *selectors: Dict[str, Any]) -> Dict[str, Any]:
        """合并多个选择器"""
        result = {}
        for selector in selectors:
            if selector:
                net_utils.dict_merge(result, selector)
        return result


class StandardSelectorBuilder(SelectorBuilder):
    """标准选择器构建器"""
    
    def __init__(self, base_selector: Optional[Dict[str, Any]] = None):
        super().__init__(base_selector)
        self.custom_config = {}
        self.overrides = {}
    
    def with_config(self, config: Dict[str, Any]) -> 'StandardSelectorBuilder':
        """添加自定义配置"""
        self.custom_config = config
        return self
    
    def with_overrides(self, overrides: Dict[str, Any]) -> 'StandardSelectorBuilder':
        """添加覆盖配置"""
        self.overrides = overrides
        return self
    
    def with_user_id(self, user_id_selector: Optional[str]) -> 'StandardSelectorBuilder':
        """设置用户ID选择器"""
        self.overrides['user_id'] = user_id_selector
        return self
    
    def with_detail_source(self, name: str, source_config: Dict[str, Any]) -> 'StandardSelectorBuilder':
        """添加详情源配置"""
        if 'detail_sources' not in self.overrides:
            self.overrides['detail_sources'] = {}
        self.overrides['detail_sources'][name] = source_config
        return self
    
    def with_detail(self, name: str, detail_config: Dict[str, Any]) -> 'StandardSelectorBuilder':
        """添加详情字段配置"""
        if 'details' not in self.overrides:
            self.overrides['details'] = {}
        self.overrides['details'][name] = detail_config
        return self
    
    def build(self) -> Dict[str, Any]:
        """构建选择器"""
        # 从基础选择器开始
        result = self.base_selector.copy()
        
        # 合并自定义配置
        if self.custom_config:
            net_utils.dict_merge(result, self.custom_config)
        
        # 应用覆盖配置
        if self.overrides:
            net_utils.dict_merge(result, self.overrides)
        
        return result


class ConfigDrivenSelectorBuilder(SelectorBuilder):
    """配置驱动的选择器构建器"""
    
    def __init__(self, base_selector: Optional[Dict[str, Any]] = None):
        super().__init__(base_selector)
        self.site_config = {}
        self.global_config = {}
    
    def with_site_config(self, site_name: str, config: Dict[str, Any]) -> 'ConfigDrivenSelectorBuilder':
        """设置站点特定配置"""
        self.site_config[site_name] = config
        return self
    
    def with_global_config(self, config: Dict[str, Any]) -> 'ConfigDrivenSelectorBuilder':
        """设置全局配置"""
        self.global_config = config
        return self
    
    def build_for_site(self, site_name: str) -> Dict[str, Any]:
        """为特定站点构建选择器"""
        # 从基础选择器开始
        result = self.base_selector.copy()
        
        # 应用全局配置
        if self.global_config:
            net_utils.dict_merge(result, self.global_config)
        
        # 应用站点特定配置
        if site_name in self.site_config:
            net_utils.dict_merge(result, self.site_config[site_name])
        
        return result
    
    def build(self) -> Dict[str, Any]:
        """构建默认选择器"""
        result = self.base_selector.copy()
        if self.global_config:
            net_utils.dict_merge(result, self.global_config)
        return result


class SelectorBuilderFactory:
    """选择器构建器工厂"""
    
    @staticmethod
    def create_standard_builder(base_selector: Optional[Dict[str, Any]] = None) -> StandardSelectorBuilder:
        """创建标准选择器构建器"""
        return StandardSelectorBuilder(base_selector)
    
    @staticmethod
    def create_config_driven_builder(base_selector: Optional[Dict[str, Any]] = None) -> ConfigDrivenSelectorBuilder:
        """创建配置驱动的选择器构建器"""
        return ConfigDrivenSelectorBuilder(base_selector)
    
    @staticmethod
    def create_builder_for_site(site_name: str, base_selector: Optional[Dict[str, Any]] = None) -> SelectorBuilder:
        """为特定站点创建合适的构建器"""
        # 根据站点特性选择合适的构建器
        if site_name in ['hdsky', 'btschool']:
            # 这些站点需要特殊处理
            return StandardSelectorBuilder(base_selector)
        else:
            # 其他站点使用配置驱动
            return ConfigDrivenSelectorBuilder(base_selector)


# 便捷函数
def build_selector(base_selector: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """构建选择器的便捷函数"""
    builder = StandardSelectorBuilder(base_selector)
    
    if 'user_id' in kwargs:
        builder.with_user_id(kwargs['user_id'])
    
    if 'detail_sources' in kwargs:
        for name, source in kwargs['detail_sources'].items():
            builder.with_detail_source(name, source)
    
    if 'details' in kwargs:
        for name, detail in kwargs['details'].items():
            builder.with_detail(name, detail)
    
    return builder.build()


def merge_selectors(*selectors: Dict[str, Any]) -> Dict[str, Any]:
    """合并多个选择器的便捷函数"""
    result = {}
    for selector in selectors:
        if selector:
            net_utils.dict_merge(result, selector)
    return result
