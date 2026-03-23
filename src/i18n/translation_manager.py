"""
MINGDA SignMaker - 翻译管理器

管理 Qt 翻译系统，包括：
- 加载和切换语言
- 管理 QTranslator 实例
- 保存用户语言偏好（使用 QSettings）
- RTL 语言支持
"""

from pathlib import Path
from typing import Optional, Dict, Callable, List
import sys

from PySide6.QtCore import QObject, Signal, QTranslator, QLocale, QSettings
from PySide6.QtWidgets import QApplication


# 支持的语言列表
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "zh_CN": "中文",
    "en_US": "English",
    "ru_RU": "Русский",
    "uk_UA": "Українська",
    "de_DE": "Deutsch",
    "fr_FR": "Français",
    "es_ES": "Español",
    "pt_BR": "Português",
    "it_IT": "Italiano",
    "he_IL": "עברית",
    "ar_SA": "العربية",
    "ja_JP": "日本語",
    "ko_KR": "한국어",
    "tr_TR": "Türkçe"
}

# 从右到左 (RTL) 语言
RTL_LANGUAGES = {"he_IL", "ar_SA"}


class TranslationManager(QObject):
    """
    翻译管理器

    负责加载和切换应用程序的语言。
    使用 Qt 的 QTranslator 系统加载 .qm 文件。
    使用 QSettings 保存语言偏好。
    """

    # 语言变更信号
    language_changed = Signal(str)
    DEFAULT_LANGUAGE = "en_US"

    def __init__(self, app: QApplication, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._app = app
        self._translator: Optional[QTranslator] = None
        self._qt_translator: Optional[QTranslator] = None

        # 翻译文件目录（兼容 PyInstaller 打包环境）
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后，资源在 sys._MEIPASS 目录下
            base_dir = Path(sys._MEIPASS)
        else:
            # 开发环境，从源码目录向上查找
            base_dir = Path(__file__).parent.parent.parent
        self._translations_dir = base_dir / "translations"

        # 使用 QSettings 保存语言偏好（与 SettingsManager 使用相同的组织/应用名称）
        self._settings = QSettings("MINGDA", "SignMaker")
        self._current_language = self._detect_system_language()

        # 语言变更回调列表
        self._callbacks: List[Callable[[], None]] = []

        # 加载保存的语言偏好
        self._load_saved_language()

    @classmethod
    def _match_supported_language(cls, lang_code: str) -> Optional[str]:
        """将系统语言代码映射到当前应用支持的语言代码。"""
        if not lang_code:
            return None

        normalized = QLocale(lang_code).name()
        if normalized in SUPPORTED_LANGUAGES:
            return normalized

        language_prefix = normalized.split("_", 1)[0]
        for supported_lang in SUPPORTED_LANGUAGES:
            if supported_lang.split("_", 1)[0] == language_prefix:
                return supported_lang

        return None

    @classmethod
    def _detect_system_language(cls) -> str:
        """检测系统语言，匹配不到时回退到英语。"""
        system_locale = QLocale.system()
        candidates: List[str] = []

        for lang_code in system_locale.uiLanguages():
            if lang_code and lang_code not in candidates:
                candidates.append(lang_code)

        system_name = system_locale.name()
        if system_name and system_name not in candidates:
            candidates.append(system_name)

        for lang_code in candidates:
            matched = cls._match_supported_language(lang_code)
            if matched:
                return matched

        return cls.DEFAULT_LANGUAGE

    def _load_saved_language(self):
        """加载保存的语言偏好"""
        if not self._settings.contains("language"):
            return

        saved_lang = self._settings.value("language", "", type=str)
        if saved_lang in SUPPORTED_LANGUAGES:
            self._current_language = saved_lang

    def _save_language_preference(self, lang_code: str):
        """保存语言偏好"""
        self._settings.setValue("language", lang_code)

    def _get_translation_qm_file(self, lang_code: str) -> Path:
        """获取指定语言对应的 qm 翻译文件路径。"""
        return self._translations_dir / f"signmaker_{lang_code}.qm"

    def has_language_resources(self, lang_code: str) -> bool:
        """检查指定语言的翻译资源是否可用。"""
        if lang_code not in SUPPORTED_LANGUAGES:
            return False
        return self._get_translation_qm_file(lang_code).exists()

    def set_language_preference(self, lang_code: str) -> bool:
        """保存语言偏好，等待下次启动时统一生效。"""
        if not self.has_language_resources(lang_code):
            return False

        self._save_language_preference(lang_code)
        return True

    def get_current_language(self) -> str:
        """获取当前语言代码"""
        return self._current_language

    def get_current_language_name(self) -> str:
        """获取当前语言显示名称"""
        return SUPPORTED_LANGUAGES.get(self._current_language, "中文")

    def is_rtl(self, lang_code: Optional[str] = None) -> bool:
        """
        检查语言是否为RTL（从右到左）

        Args:
            lang_code: 语言代码，为None时使用当前语言

        Returns:
            是否为RTL语言
        """
        if lang_code is None:
            lang_code = self._current_language
        return lang_code in RTL_LANGUAGES

    def load_language(self, lang_code: str) -> bool:
        """
        加载指定语言

        Args:
            lang_code: 语言代码，如 "en_US", "zh_CN"

        Returns:
            是否加载成功
        """
        if lang_code not in SUPPORTED_LANGUAGES:
            print(f"[i18n] Unsupported language: {lang_code}")
            return False

        # 移除旧的翻译器
        if self._translator is not None:
            self._app.removeTranslator(self._translator)
            self._translator = None

        if self._qt_translator is not None:
            self._app.removeTranslator(self._qt_translator)
            self._qt_translator = None

        # 中文需要加载翻译文件（因为源代码使用英文）
        qm_file = self._get_translation_qm_file(lang_code)

        if not qm_file.exists():
            # 尝试从 .ts 文件编译（开发模式）
            ts_file = self._translations_dir / f"signmaker_{lang_code}.ts"
            if ts_file.exists():
                print(f"[i18n] .qm file not found, please run pyside6-lrelease to compile translation")
            else:
                print(f"[i18n] Translation file not found: {qm_file}")
            # 即使翻译文件不存在，也切换语言（显示原文）
            self._current_language = lang_code
            self._save_language_preference(lang_code)
            self.language_changed.emit(lang_code)
            self._notify_callbacks()
            return False

        # 创建并安装翻译器
        self._translator = QTranslator(self._app)
        if self._translator.load(str(qm_file)):
            self._app.installTranslator(self._translator)
            print(f"[i18n] Loaded translation: {lang_code}")
        else:
            print(f"[i18n] Failed to load translation: {qm_file}")
            self._translator = None

        # 加载 Qt 内置组件的翻译（如对话框按钮）
        qt_qm = QLocale(lang_code).name()
        self._qt_translator = QTranslator(self._app)
        # Qt 翻译文件通常随 Qt 安装提供
        # 如果需要，可以从 Qt 安装目录复制

        old_language = self._current_language
        self._current_language = lang_code

        # 保存语言偏好
        self._save_language_preference(lang_code)

        # 发射信号
        if old_language != lang_code:
            self.language_changed.emit(lang_code)
            self._notify_callbacks()

        return True

    def register_callback(self, callback: Callable[[], None]):
        """
        注册语言变更回调

        回调函数应该调用 retranslateUi() 来更新界面文本。

        Args:
            callback: 无参数回调函数
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[], None]):
        """取消注册回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self):
        """通知所有注册的回调"""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                print(f"[i18n] Callback execution error: {e}")

    @staticmethod
    def get_available_languages() -> Dict[str, str]:
        """获取所有支持的语言"""
        return SUPPORTED_LANGUAGES.copy()


# 全局翻译管理器实例
_translation_manager: Optional[TranslationManager] = None


def get_translation_manager() -> Optional[TranslationManager]:
    """获取全局翻译管理器实例"""
    return _translation_manager


def init_translation_manager(app: QApplication) -> TranslationManager:
    """
    初始化全局翻译管理器

    Args:
        app: QApplication 实例

    Returns:
        TranslationManager 实例
    """
    global _translation_manager
    _translation_manager = TranslationManager(app)
    return _translation_manager
