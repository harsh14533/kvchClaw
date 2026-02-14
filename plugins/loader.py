# plugins/loader.py
# Automatically discovers and loads all plugins from the plugins/ folder

import os
import importlib
import inspect
from plugins.base import Plugin

def load_plugins() -> list:
    """
    Scans plugins/ folder and loads every plugin it finds.
    Returns list of plugin instances.
    """
    plugins = []
    plugin_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(plugin_dir):
        # Skip non-python files and special files
        if not filename.endswith('.py'):
            continue
        if filename.startswith('_'):
            continue
        if filename in ['base.py', 'loader.py']:
            continue
        
        module_name = filename[:-3]  # Remove .py
        
        try:
            # Import the plugin module
            module = importlib.import_module(f"plugins.{module_name}")
# Find all Plugin subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Plugin) and obj is not Plugin:
                    instance = obj()
                    plugins.append(instance)
                    print(f"🔌 Loaded plugin: {instance.name}")
                    
        except Exception as e:
            print(f"⚠️ Failed to load plugin {module_name}: {e}")
    
    return plugins

def get_plugin_prompts(plugins: list) -> str:
    """Get all plugin descriptions for AI system prompt"""
    if not plugins:
        return ""
    descriptions = [p.get_prompt_description() for p in plugins]
    return "\n".join(descriptions)

def find_plugin(plugins: list, action: str, value: str):
    """Find which plugin can handle this action"""
    for plugin in plugins:
        if plugin.can_handle(action, value):
            return plugin
    return None
