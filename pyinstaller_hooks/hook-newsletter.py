#!/usr/bin/env python3
"""PyInstaller hook for newsletter generator application.

This hook centralizes all hidden imports, data files, and binary dependencies
for the newsletter generator to reduce maintenance burden and improve build process.
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

# Get project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# =============================================================================
# HIDDEN IMPORTS
# =============================================================================

# 📋 Basic Framework Modules
basic_imports = [
    # Web Framework
    "flask", "flask_cors", "werkzeug", "jinja2", "jinja2.runtime", 
    "jinja2.loaders", "jinja2.utils",
    
    # Database & Storage
    "sqlite3", "redis", "rq", "rq.worker", "rq.job", "rq.queue",
    
    # Configuration & Environment
    "pydantic", "pydantic_settings", "python_dotenv", "dotenv",
    "yaml", "PyYAML",
    
    # HTTP & Web Scraping
    "requests", "requests.adapters", "urllib3", "urllib3.util.retry",
    "beautifulsoup4", "bs4", "feedparser",
    
    # Date & Time
    "dateutil", "dateutil.rrule", "dateutil.parser", "dateutil.tz",
    
    # Utilities
    "rich", "rich.console", "typer", "uuid", "json", "re", "time",
    "threading", "multiprocessing", "concurrent.futures",
]

# 🤖 AI/LLM Core Modules
ai_core_imports = [
    # LangChain Core
    "langchain", "langchain_core", "langchain_community",
    "langchain.callbacks", "langchain.callbacks.base",
    "langchain.prompts", "langchain.tools", "langchain.chains",
    "langchain.llms", "langchain.chat_models",
    "langchain_core.messages", "langchain_core.output_parsers", 
    "langchain_core.runnables", "langchain_core.tools",
    "langchain_core.outputs", "langchain_core.callbacks",
    
    # LangGraph
    "langgraph", "langgraph.graph", "langgraph.prebuilt",
    
    # LangSmith (monitoring)
    "langsmith", "langsmith.client",
]

# 🌐 LLM Provider Specific Modules
llm_providers = [
    # Google Gemini
    "langchain_google_genai", 
    "google", "google.generativeai", "google.ai", "google.ai.generativelanguage",
    "google.api_core", "google.auth", "google.cloud",
    "google.generativeai", "google.generativeai.client",
    "google.generativeai.types", "google.generativeai.models",
    
    # OpenAI
    "langchain_openai",
    "openai", "openai.api_resources", "openai.error",
    
    # Anthropic
    "langchain_anthropic",
    "anthropic", "anthropic.client", "anthropic.types",
    
    # API clients common modules
    "httpx", "httpx._client", "httpx._config", "httpx._models",
    "aiohttp", "aiohttp.client", "aiohttp.connector",
]

# 📧 Email & Communication
email_imports = [
    "postmarker", "postmarker.core", "postmarker.models",
    "premailer", "markdownify", "tenacity", "tenacity.stop", "tenacity.wait",
]

# 🔍 Data Processing & Analysis
data_processing = [
    "pandas", "numpy", 
    "chromadb", "faiss", "faiss.swigfaiss",
    "sentence_transformers",  # If used for embeddings
]

# 🔒 Security & Monitoring
security_monitoring = [
    "sentry_sdk", "sentry_sdk.integrations", "sentry_sdk.integrations.flask",
    "sentry_sdk.integrations.logging",
]

# 🔧 System & OS specific
system_imports = [
    "platform", "subprocess", "pathlib", "tempfile", "shutil",
    "signal", "atexit", "traceback", "logging", "logging.config",
]

# ⚙️ Newsletter specific modules
newsletter_modules = [
    "newsletter", "newsletter.cli", "newsletter.main", "newsletter.settings",
    "newsletter.collect", "newsletter.sources", "newsletter.article_filter",
    "newsletter.compose", "newsletter.deliver", "newsletter.summarize",
    "newsletter.chains", "newsletter.graph", "newsletter.tools",
    "newsletter.llm_factory", "newsletter.cost_tracking", "newsletter.scoring",
    "newsletter.config", "newsletter.config_manager", "newsletter.centralized_settings",
    "newsletter.template_manager", "newsletter.date_utils", "newsletter.html_utils",
    "newsletter.compat_env", "newsletter.logging_conf",
    "newsletter.security", "newsletter.security.config", 
    "newsletter.security.middleware", "newsletter.security.logging",
    "newsletter.security.validation",
    "newsletter.utils", "newsletter.utils.logger", "newsletter.utils.error_handling",
    "newsletter.utils.file_naming", "newsletter.utils.subprocess_utils",
    "newsletter.utils.test_mode", "newsletter.utils.convert_legacy_data",
    "newsletter.utils.shutdown_manager",
    
    # Latest additional modules
    "newsletter.template_config", "newsletter.email_processing",
    "newsletter.file_utils", "newsletter.validation",
]

# 🌐 Web specific modules
web_modules = [
    "web", "web.app", "web.tasks", "web.mail", "web.suggest", 
    "web.worker", "web.schedule_runner", "web.web_types",
    "web.graceful_shutdown",
    
    # Binary compatibility modules (important!)
    "web.binary_compatibility", "binary_compatibility",
]

# Combine all hidden imports
hiddenimports = (
    basic_imports + ai_core_imports + llm_providers + email_imports +
    data_processing + security_monitoring + system_imports +
    newsletter_modules + web_modules
)

# =============================================================================
# DATA FILES
# =============================================================================

# Define data files to be included in the bundle
datas = [
    (os.path.join(project_root, 'templates'), 'templates'),
    (os.path.join(project_root, 'web', 'templates'), 'templates'),
    (os.path.join(project_root, 'web', 'static'), 'static'),
    (os.path.join(project_root, 'web', 'web_types.py'), 'web'),
    (os.path.join(project_root, 'newsletter'), 'newsletter'),
    (os.path.join(project_root, 'config.yml'), '.'),
    (os.path.join(project_root, 'config'), 'config'),
    # Note: .env file is NOT included in bundle for security
    # It should be placed next to the exe file by build script
]

# Filter out non-existent data files
datas = [(src, dst) for src, dst in datas if os.path.exists(src)]

# =============================================================================
# BINARY FILES
# =============================================================================

# Define binary files
binaries = [
    (os.path.join(project_root, 'web', 'web_types.py'), 'web'),
    (os.path.join(project_root, 'web', 'binary_compatibility.py'), 'web'),
]

# Filter out non-existent binary files
binaries = [(src, dst) for src, dst in binaries if os.path.exists(src)]

# =============================================================================
# COLLECT ALL PACKAGES
# =============================================================================

# Packages to collect entirely (this replaces --collect-all options)
collect_all_packages = [
    'newsletter',
    'web', 
    'langchain',
    'langchain_core',
    'langchain_google_genai',
    'langchain_openai',
    'langchain_anthropic',
    'langgraph',
]

# Collect data files from packages
for package in collect_all_packages:
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package)
        if package_datas:
            datas.extend(package_datas)
        if package_binaries:
            binaries.extend(package_binaries)
        if package_hiddenimports:
            hiddenimports.extend(package_hiddenimports)
    except Exception:
        # Ignore packages that don't exist or can't be collected
        pass

# =============================================================================
# COLLECT DYNAMIC LIBRARIES
# =============================================================================

# Collect dynamic libraries for specific packages
collect_libs_packages = ['google', 'grpc', 'grpcio']

for package in collect_libs_packages:
    try:
        libs = collect_dynamic_libs(package)
        if libs:
            binaries.extend(libs)
    except Exception:
        # Ignore packages that don't exist
        pass

# =============================================================================
# EXCLUDES
# =============================================================================

# Modules to exclude (optional - helps reduce bundle size)
excludes = [
    # Exclude test modules
    'tests', 'test', 'pytest', 'unittest',
    # Exclude development tools
    'IPython', 'jupyter', 'notebook',
    # Exclude unused GUI toolkits
    'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    # Exclude matplotlib if not used
    'matplotlib',
]

print(f"[HOOK] Newsletter hook loaded:")
print(f"  - Hidden imports: {len(hiddenimports)}")
print(f"  - Data files: {len(datas)}")
print(f"  - Binary files: {len(binaries)}")
print(f"  - Excluded modules: {len(excludes)}")