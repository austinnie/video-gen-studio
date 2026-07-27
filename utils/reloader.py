import importlib
import sys
from typing import List, Optional, Callable


class Reloader:
    def __init__(self):
        self.modules = [
            'config.settings',
            'utils.logger',
            'utils.memory',
            'utils.ffmpeg_utils',
            'core.model_loader',
            'core.generator',
            'ui.widgets.prompt',
            'ui.widgets.model',
            'ui.widgets.params',
            'ui.widgets.progress',
            'ui.widgets.preview',
            'ui.app',
        ]
        self.rebuild_callback = None

    def set_rebuild_callback(self, cb):
        self.rebuild_callback = cb

    def reload_all(self):
        success, failed = [], []
        for name in self.modules:
            if name in sys.modules:
                try:
                    importlib.reload(sys.modules[name])
                    success.append(name)
                except Exception as e:
                    print(f"❌ {name}: {e}")
                    failed.append(name)

        if self.rebuild_callback:
            self.rebuild_callback()

        print(f"✅ 重载: {len(success)} 个模块")
        return success, failed


reloader = Reloader()