"""
Newsletter Generator - LangChain과 LangGraph 기반 뉴스레터 생성 패키지

이 패키지는 키워드를 기반으로 최신 뉴스를 수집하고 요약하여
HTML 형식의 뉴스레터를 자동으로 생성하는 기능을 제공합니다.
"""

import os
from datetime import datetime

# Set the generation date environment variable with current date and time
os.environ["GENERATION_DATE"] = datetime.now().strftime("%Y-%m-%d")
os.environ["GENERATION_TIMESTAMP"] = datetime.now().strftime("%H:%M:%S")

__version__ = "0.2.0"

# Lazy import system to avoid import chain issues during test collection
def __getattr__(name):
    """Lazy import system - only import modules when actually accessed"""
    module_map = {
        'cli': 'cli',
        'collect': 'collect', 
        'tools': 'tools',
        'chains': 'chains',
        'sources': 'sources',
        'article_filter': 'article_filter',
        'deliver': 'deliver',
        'config': 'config',
        'main': 'main',
        'compose': 'compose',
        'scoring': 'scoring',
        'template_manager': 'template_manager',
        'cost_tracking': 'cost_tracking',
        'date_utils': 'date_utils',
        'html_utils': 'html_utils',
        'llm_factory': 'llm_factory',
        'centralized_settings': 'centralized_settings',
        'security': 'security',
        'config_manager': 'config_manager',
        'get_settings': 'centralized_settings',
        'generate_newsletter': 'main'
    }
    
    if name in module_map:
        try:
            from importlib import import_module
            module_name = module_map[name]
            
            if name == 'config_manager':
                module = import_module(f'.{module_name}', __name__)
                return getattr(module, 'config_manager')
            elif name == 'get_settings':
                module = import_module(f'.{module_name}', __name__)
                return getattr(module, 'get_settings')
            elif name == 'generate_newsletter':
                module = import_module(f'.{module_name}', __name__)
                return getattr(module, 'generate_newsletter')
            else:
                return import_module(f'.{module_name}', __name__)
        except ImportError as e:
            # Import failed - return None or raise depending on context
            import sys
            if "pytest" not in sys.modules:
                print(f"Warning: Could not lazy import {name}: {e}")
            raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
