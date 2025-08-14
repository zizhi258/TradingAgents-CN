"""
依赖检查工具
检查各种API客户端的依赖是否可用
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('dependency_checker')


@dataclass
class DependencyResult:
    """依赖检查结果"""
    provider: str
    available: bool
    missing_packages: List[str]
    error_message: str = ""


class DependencyChecker:
    """依赖检查器"""
    
    def __init__(self):
        """初始化依赖检查器"""
        self.dependency_map = {
            'google_ai': ['google-generativeai'],
            'openai': ['openai'],
            'dashscope': ['dashscope'],
            'siliconflow': ['requests'],  # SiliconFlow uses standard requests
            'deepseek': ['requests']  # DeepSeek uses standard requests
        }
    
    def check_provider_dependencies(self, provider: str) -> DependencyResult:
        """
        检查特定提供商的依赖
        
        Args:
            provider: 提供商名称
            
        Returns:
            DependencyResult: 检查结果
        """
        if provider not in self.dependency_map:
            return DependencyResult(
                provider=provider,
                available=False,
                missing_packages=[],
                error_message=f"未知的提供商: {provider}"
            )
        
        required_packages = self.dependency_map[provider]
        missing_packages = []
        
        for package in required_packages:
            try:
                if package == 'google-generativeai':
                    import google.generativeai
                elif package == 'openai':
                    import openai
                elif package == 'dashscope':
                    import dashscope
                elif package == 'requests':
                    import requests
                else:
                    # 通用导入检查
                    __import__(package)
                    
            except ImportError as e:
                missing_packages.append(package)
                logger.debug(f"包 {package} 不可用: {e}")
        
        is_available = len(missing_packages) == 0
        error_msg = ""
        
        if not is_available:
            error_msg = f"缺少依赖包: {', '.join(missing_packages)}"
        
        result = DependencyResult(
            provider=provider,
            available=is_available,
            missing_packages=missing_packages,
            error_message=error_msg
        )
        
        logger.debug(f"依赖检查 {provider}: {'可用' if is_available else '不可用'} - {error_msg}")
        return result
    
    def check_all_providers(self) -> Dict[str, DependencyResult]:
        """
        检查所有提供商的依赖
        
        Returns:
            Dict[str, DependencyResult]: 所有提供商的检查结果
        """
        results = {}
        
        for provider in self.dependency_map:
            results[provider] = self.check_provider_dependencies(provider)
        
        available_providers = [p for p, r in results.items() if r.available]
        unavailable_providers = [p for p, r in results.items() if not r.available]
        
        logger.info(f"依赖检查完成 - 可用: {available_providers}, 不可用: {unavailable_providers}")
        
        return results
    
    def get_available_providers(self) -> List[str]:
        """
        获取所有可用的提供商列表
        
        Returns:
            List[str]: 可用的提供商名称列表
        """
        results = self.check_all_providers()
        return [provider for provider, result in results.items() if result.available]
    
    def filter_config_by_availability(self, config: Dict[str, any]) -> Dict[str, any]:
        """
        根据依赖可用性过滤配置
        
        Args:
            config: 原始配置字典
            
        Returns:
            Dict[str, any]: 过滤后的配置字典
        """
        filtered_config = config.copy()
        dependency_results = self.check_all_providers()
        
        providers_to_check = ['google_ai', 'openai', 'dashscope', 'siliconflow']
        
        for provider in providers_to_check:
            if provider in filtered_config:
                result = dependency_results.get(provider)
                if result and not result.available:
                    # 禁用不可用的提供商
                    if isinstance(filtered_config[provider], dict):
                        filtered_config[provider]['enabled'] = False
                        logger.warning(f"由于依赖缺失，禁用了 {provider}: {result.error_message}")
                    else:
                        # 如果配置不是字典，则移除整个配置项
                        filtered_config.pop(provider, None)
                        logger.warning(f"由于依赖缺失，移除了 {provider} 配置: {result.error_message}")
        
        return filtered_config
    
    def validate_config(self, config: Dict[str, any]) -> Tuple[bool, List[str]]:
        """
        验证配置是否有可用的提供商
        
        Args:
            config: 配置字典
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        available_providers = []
        
        dependency_results = self.check_all_providers()
        
        providers_to_check = ['google_ai', 'openai', 'dashscope', 'siliconflow']
        
        for provider in providers_to_check:
            if provider in config:
                provider_config = config[provider]
                if isinstance(provider_config, dict) and provider_config.get('enabled', False):
                    result = dependency_results.get(provider)
                    if result and result.available:
                        available_providers.append(provider)
                    elif result:
                        errors.append(f"{provider}: {result.error_message}")
        
        if not available_providers:
            errors.append("没有可用的API提供商")
            return False, errors
        
        logger.info(f"配置验证完成 - 可用提供商: {available_providers}")
        return True, []


# 创建全局依赖检查器实例
dependency_checker = DependencyChecker()


def check_dependencies(*providers: str) -> Dict[str, bool]:
    """
    便捷函数：检查指定提供商的依赖
    
    Args:
        *providers: 提供商名称列表
        
    Returns:
        Dict[str, bool]: 提供商可用性映射
    """
    if not providers:
        providers = ['google_ai', 'openai', 'dashscope', 'siliconflow']
    
    results = {}
    for provider in providers:
        result = dependency_checker.check_provider_dependencies(provider)
        results[provider] = result.available
    
    return results


def get_safe_config(original_config: Dict[str, any]) -> Dict[str, any]:
    """
    便捷函数：获取安全的配置（禁用不可用的提供商）
    
    Args:
        original_config: 原始配置
        
    Returns:
        Dict[str, any]: 安全的配置
    """
    return dependency_checker.filter_config_by_availability(original_config)