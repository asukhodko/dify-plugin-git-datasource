"""
Git Datasource Plugin for Dify.

Entry point for the plugin.
"""

from dify_plugin import DifyPluginEnv, Plugin

plugin = Plugin(DifyPluginEnv())

if __name__ == "__main__":
    plugin.run()
