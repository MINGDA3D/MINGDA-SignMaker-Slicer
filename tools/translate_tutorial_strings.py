#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add Tutorial-related translations to all Qt TS files."""

import re
from pathlib import Path


TRANSLATIONS = {
    "zh_CN": {
        "Tutorial": "教程",
        "Open Tutorial Failed": "打开教程失败",
        "Failed to open the tutorial playlist in the default browser.": "无法在默认浏览器中打开教程播放列表。",
    },
    "en_US": {
        "Tutorial": "Tutorial",
        "Open Tutorial Failed": "Open Tutorial Failed",
        "Failed to open the tutorial playlist in the default browser.": "Failed to open the tutorial playlist in the default browser.",
    },
    "ru_RU": {
        "Tutorial": "Видеоуроки",
        "Open Tutorial Failed": "Не удалось открыть видеоуроки",
        "Failed to open the tutorial playlist in the default browser.": "Не удалось открыть плейлист с видеоуроками в браузере по умолчанию.",
    },
    "uk_UA": {
        "Tutorial": "Відеоуроки",
        "Open Tutorial Failed": "Не вдалося відкрити відеоуроки",
        "Failed to open the tutorial playlist in the default browser.": "Не вдалося відкрити плейлист з відеоуроками у типовому браузері.",
    },
    "de_DE": {
        "Tutorial": "Tutorial",
        "Open Tutorial Failed": "Tutorial konnte nicht geöffnet werden",
        "Failed to open the tutorial playlist in the default browser.": "Die Tutorial-Playlist konnte nicht im Standardbrowser geöffnet werden.",
    },
    "fr_FR": {
        "Tutorial": "Tutoriel",
        "Open Tutorial Failed": "Ouverture du tutoriel impossible",
        "Failed to open the tutorial playlist in the default browser.": "Impossible d’ouvrir la playlist du tutoriel dans le navigateur par défaut.",
    },
    "es_ES": {
        "Tutorial": "Tutorial",
        "Open Tutorial Failed": "No se pudo abrir el tutorial",
        "Failed to open the tutorial playlist in the default browser.": "No se pudo abrir la lista de reproducción del tutorial en el navegador predeterminado.",
    },
    "pt_BR": {
        "Tutorial": "Tutorial",
        "Open Tutorial Failed": "Falha ao abrir o tutorial",
        "Failed to open the tutorial playlist in the default browser.": "Não foi possível abrir a playlist do tutorial no navegador padrão.",
    },
    "it_IT": {
        "Tutorial": "Tutorial",
        "Open Tutorial Failed": "Impossibile aprire il tutorial",
        "Failed to open the tutorial playlist in the default browser.": "Impossibile aprire la playlist del tutorial nel browser predefinito.",
    },
    "he_IL": {
        "Tutorial": "מדריכים",
        "Open Tutorial Failed": "פתיחת המדריכים נכשלה",
        "Failed to open the tutorial playlist in the default browser.": "לא ניתן לפתוח את פלייליסט המדריכים בדפדפן ברירת המחדל.",
    },
    "ar_SA": {
        "Tutorial": "الدروس",
        "Open Tutorial Failed": "تعذر فتح الدروس",
        "Failed to open the tutorial playlist in the default browser.": "تعذر فتح قائمة تشغيل الدروس في المتصفح الافتراضي.",
    },
    "ja_JP": {
        "Tutorial": "チュートリアル",
        "Open Tutorial Failed": "チュートリアルを開けませんでした",
        "Failed to open the tutorial playlist in the default browser.": "デフォルトのブラウザーでチュートリアル再生リストを開けませんでした。",
    },
    "ko_KR": {
        "Tutorial": "튜토리얼",
        "Open Tutorial Failed": "튜토리얼을 열 수 없습니다",
        "Failed to open the tutorial playlist in the default browser.": "기본 브라우저에서 튜토리얼 재생목록을 열 수 없습니다.",
    },
    "tr_TR": {
        "Tutorial": "Eğitim",
        "Open Tutorial Failed": "Eğitim açılamadı",
        "Failed to open the tutorial playlist in the default browser.": "Eğitim oynatma listesi varsayılan tarayıcıda açılamadı.",
    },
}


def update_file(lang_code: str) -> None:
    ts_file = Path(__file__).parent.parent / "translations" / f"signmaker_{lang_code}.ts"
    if not ts_file.exists():
        print(f"[SKIP] {lang_code}: file not found")
        return

    content = ts_file.read_text(encoding="utf-8")
    updated = 0

    for source, target in TRANSLATIONS[lang_code].items():
        pattern = rf"(<source>{re.escape(source)}</source>\s*\n\s*)<translation[^>]*>.*?</translation>"

        def replace_func(match):
            nonlocal updated
            updated += 1
            return f"{match.group(1)}<translation>{target}</translation>"

        content = re.sub(pattern, replace_func, content)

    ts_file.write_text(content, encoding="utf-8")
    print(f"[OK] {lang_code}: updated {updated} entries")


if __name__ == "__main__":
    for language in TRANSLATIONS:
        update_file(language)
    print("\nDone! Run 'python tools/update_translations.py compile' to compile.")
