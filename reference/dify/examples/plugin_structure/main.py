"""
main.py — точка входа Dify плагина.

Верифицировано по: dify-plugin-sdks/python/examples/notion_datasource/main.py
"""

from dify_plugin import Plugin, DifyPluginEnv

plugin = Plugin(DifyPluginEnv())

if __name__ == "__main__":
    plugin.run()
