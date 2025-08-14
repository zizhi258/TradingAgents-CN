"""
API密钥验证工具
"""
import os
import requests
from typing import Dict, Optional, Tuple


def validate_api_keys() -> Dict[str, Dict[str, any]]:
    """验证所有配置的API密钥
    
    Returns:
        Dict: 各个提供商的验证结果
    """
    results = {}
    
    # 验证DeepSeek API
    results['deepseek'] = validate_deepseek_api()
    
    # 验证Google AI API
    results['google'] = validate_google_ai_api()
    
    # 验证SiliconFlow API
    results['siliconflow'] = validate_siliconflow_api()
    
    return results


def validate_deepseek_api() -> Dict[str, any]:
    """验证DeepSeek API密钥"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    if not api_key or api_key.startswith('sk-xxxxxxxx'):
        return {
            'valid': False,
            'error': 'API密钥未配置或为示例密钥',
            'suggestion': '请在.env文件中配置有效的DEEPSEEK_API_KEY'
        }
    
    try:
        # 简单的模型列表请求来验证密钥
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'{base_url}/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                'valid': True,
                'message': 'DeepSeek API密钥验证成功'
            }
        elif response.status_code == 401:
            return {
                'valid': False,
                'error': 'DeepSeek API密钥无效或已过期',
                'suggestion': '请检查DEEPSEEK_API_KEY是否正确'
            }
        else:
            return {
                'valid': False,
                'error': f'DeepSeek API请求失败: HTTP {response.status_code}',
                'suggestion': '请检查网络连接和API服务状态'
            }
            
    except requests.exceptions.Timeout:
        return {
            'valid': False,
            'error': 'DeepSeek API请求超时',
            'suggestion': '请检查网络连接'
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f'DeepSeek API验证出错: {str(e)}',
            'suggestion': '请检查网络连接和配置'
        }


def validate_google_ai_api() -> Dict[str, any]:
    """验证Google AI API密钥"""
    api_key = (
        os.getenv('GEMINI_API_KEY')
        or os.getenv('GOOGLE_AI_API_KEY')
        or os.getenv('GOOGLE_GENAI_API_KEY')
        or os.getenv('GOOGLE_API_KEY')
    )
    
    if not api_key or api_key.startswith('AIzaSyXXXX'):
        return {
            'valid': False,
            'error': 'Google AI API密钥未配置或为示例密钥',
            'suggestion': '请在.env文件中配置有效的GEMINI_API_KEY'
        }
    
    try:
        # 使用Google AI的简单API请求验证
        response = requests.get(
            f'https://generativelanguage.googleapis.com/v1/models?key={api_key}',
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                'valid': True,
                'message': 'Google AI API密钥验证成功'
            }
        elif response.status_code == 400:
            data = response.json()
            if 'API_KEY_INVALID' in data.get('error', {}).get('status', ''):
                return {
                    'valid': False,
                    'error': 'Google AI API密钥无效',
                    'suggestion': '请检查GEMINI_API_KEY是否正确'
                }
            else:
                return {
                    'valid': False,
                    'error': f'Google AI API请求错误: {data}',
                    'suggestion': '请检查API密钥和配置'
                }
        else:
            return {
                'valid': False,
                'error': f'Google AI API请求失败: HTTP {response.status_code}',
                'suggestion': '请检查网络连接和API服务状态'
            }
            
    except Exception as e:
        return {
            'valid': False,
            'error': f'Google AI API验证出错: {str(e)}',
            'suggestion': '请检查网络连接和配置'
        }


def validate_siliconflow_api() -> Dict[str, any]:
    """验证SiliconFlow API密钥"""
    api_key = os.getenv('SILICONFLOW_API_KEY')
    base_url = os.getenv('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
    
    if not api_key or api_key.startswith('sk-xxxxxxxx'):
        return {
            'valid': False,
            'error': 'SiliconFlow API密钥未配置或为示例密钥',
            'suggestion': '请在.env文件中配置有效的SILICONFLOW_API_KEY'
        }
    
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'{base_url}/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                'valid': True,
                'message': 'SiliconFlow API密钥验证成功'
            }
        elif response.status_code == 401:
            return {
                'valid': False,
                'error': 'SiliconFlow API密钥无效或已过期',
                'suggestion': '请检查SILICONFLOW_API_KEY是否正确'
            }
        else:
            return {
                'valid': False,
                'error': f'SiliconFlow API请求失败: HTTP {response.status_code}',
                'suggestion': '请检查网络连接和API服务状态'
            }
            
    except Exception as e:
        return {
            'valid': False,
            'error': f'SiliconFlow API验证出错: {str(e)}',
            'suggestion': '请检查网络连接和配置'
        }


def get_api_key_status_summary() -> Tuple[bool, str, Dict[str, str]]:
    """获取API密钥状态摘要
    
    Returns:
        Tuple: (是否有任何可用的API, 状态消息, 详细信息)
    """
    results = validate_api_keys()
    
    valid_providers = []
    invalid_providers = []
    suggestions = {}
    
    for provider, result in results.items():
        if result['valid']:
            valid_providers.append(provider)
        else:
            invalid_providers.append(provider)
            suggestions[provider] = result['suggestion']
    
    if len(valid_providers) > 0:
        status_msg = f"✅ 可用API: {', '.join(valid_providers)}"
        if len(invalid_providers) > 0:
            status_msg += f" | ⚠️ 需要配置: {', '.join(invalid_providers)}"
        return True, status_msg, suggestions
    else:
        status_msg = f"❌ 所有API密钥都需要配置: {', '.join(invalid_providers)}"
        return False, status_msg, suggestions
