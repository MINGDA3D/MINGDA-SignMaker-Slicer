"""
MINGDA SignMaker - 国际化 (i18n) 模块

使用 Qt 官方的 .ts/.qm 翻译系统，支持14种语言：
- 中文 (zh_CN)
- English (en_US)
- Русский (ru_RU)
- Українська (uk_UA)
- Deutsch (de_DE)
- Français (fr_FR)
- Español (es_ES)
- Português (pt_BR)
- Italiano (it_IT)
- עברית (he_IL)
- العربية (ar_SA)
- 日本語 (ja_JP)
- 한국어 (ko_KR)
- Türkçe (tr_TR)

使用方式:
    from src.i18n import TranslationManager

    # 在 main.py 中初始化
    app = QApplication(sys.argv)
    translation_manager = TranslationManager(app)
    translation_manager.load_language("en_US")

    # 在 QWidget 中使用 self.tr() 标记可翻译字符串
    self.setWindowTitle(self.tr("MINGDA SignMaker"))
"""

from .translation_manager import (
    TranslationManager,
    get_translation_manager,
    init_translation_manager,
    SUPPORTED_LANGUAGES,
    RTL_LANGUAGES
)

__all__ = [
    'TranslationManager',
    'get_translation_manager',
    'init_translation_manager',
    'SUPPORTED_LANGUAGES',
    'RTL_LANGUAGES'
]
