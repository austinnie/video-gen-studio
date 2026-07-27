import importlib
import sys
from typing import List, Optional, Callable


class Reloader:
    """热重载管理器 - 参考 sd-gui 实现"""

    def __init__(self):
        # 按依赖顺序排列（先加载底层模块，再加载上层模块）
        self.modules = [
            # 配置
            'config.settings',
            # 工具
            'utils.logger',
            'utils.memory',
            'utils.ffmpeg_utils',
            'utils.reloader',
            # 核心
            'core.model_loader',
            'core.generator',
            # UI 控件
            'ui.widgets.prompt',
            'ui.widgets.model',
            'ui.widgets.params',
            'ui.widgets.progress',
            'ui.widgets.preview',
            'ui.widgets',
            # 主 UI
            'ui.app',
        ]
        self.rebuild_callback = None
        self._reload_count = 0

    def set_rebuild_callback(self, cb: Callable):
        self.rebuild_callback = cb

    def reload_all(self) -> tuple:
        """执行完整热重载"""
        self._reload_count += 1

        print("\n" + "=" * 60)
        print(f"🔄 热重载 (第 {self._reload_count} 次)")
        print("=" * 60)

        success_list = []
        failed_list = []

        for module_name in self.modules:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    print(f"   ✅ {module_name}")
                    success_list.append(module_name)
                else:
                    # 尝试导入
                    try:
                        importlib.import_module(module_name)
                        print(f"   ✅ {module_name} (新导入)")
                        success_list.append(module_name)
                    except ImportError:
                        print(f"   ⚠️ {module_name} (跳过)")
            except Exception as e:
                print(f"   ❌ {module_name}: {e}")
                failed_list.append(module_name)

        # 重建 UI
        if self.rebuild_callback:
            try:
                print("   🔨 重建 UI...")
                self.rebuild_callback()
                print("   ✅ UI 重建完成")
            except Exception as e:
                print(f"   ❌ UI 重建失败: {e}")
                import traceback
                traceback.print_exc()

        print("=" * 60)
        print(f"📊 重载完成: 成功 {len(success_list)} 个, 失败 {len(failed_list)} 个")
        print("=" * 60)

        return success_list, failed_list


reloader = Reloader()