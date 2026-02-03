#!/usr/bin/env python3
"""
Add UI translations for PresetThumbnail and ShellPanel contexts.
"""

import os
import re

# Translations for PresetThumbnail context
PRESET_THUMBNAIL_TRANSLATIONS = {
    "Width": {
        "zh_CN": "宽度",
        "en_US": "Width",
        "ru_RU": "Ширина",
        "uk_UA": "Ширина",
        "de_DE": "Breite",
        "fr_FR": "Largeur",
        "es_ES": "Ancho",
        "pt_BR": "Largura",
        "it_IT": "Larghezza",
        "he_IL": "רוחב",
        "ar_SA": "العرض",
        "ja_JP": "幅",
        "ko_KR": "너비",
        "tr_TR": "Genişlik",
    },
}

# Translations for ShellPanel context
SHELL_PANEL_TRANSLATIONS = {
    "points": {
        "zh_CN": "点",
        "en_US": " points",
        "ru_RU": " точек",
        "uk_UA": " точок",
        "de_DE": " Punkte",
        "fr_FR": " points",
        "es_ES": " puntos",
        "pt_BR": " pontos",
        "it_IT": " punti",
        "he_IL": " נקודות",
        "ar_SA": " نقاط",
        "ja_JP": "点",
        "ko_KR": "점",
        "tr_TR": " nokta",
    },
    "No profile selected": {
        "zh_CN": "未选择轮廓",
        "en_US": "No profile selected",
        "ru_RU": "Профиль не выбран",
        "uk_UA": "Профіль не вибрано",
        "de_DE": "Kein Profil ausgewählt",
        "fr_FR": "Aucun profil sélectionné",
        "es_ES": "Ningún perfil seleccionado",
        "pt_BR": "Nenhum perfil selecionado",
        "it_IT": "Nessun profilo selezionato",
        "he_IL": "לא נבחר פרופיל",
        "ar_SA": "لم يتم تحديد ملف تعريف",
        "ja_JP": "プロファイルが選択されていません",
        "ko_KR": "프로필이 선택되지 않음",
        "tr_TR": "Profil seçilmedi",
    },
}


def generate_context_block(context_name: str, translations: dict, lang_code: str) -> str:
    """Generate a context block for a .ts file."""
    lines = [f'<context>', f'    <name>{context_name}</name>']

    for source, trans_dict in translations.items():
        translation = trans_dict.get(lang_code, source)
        lines.append('    <message>')
        lines.append(f'        <source>{source}</source>')
        lines.append(f'        <translation>{translation}</translation>')
        lines.append('    </message>')

    lines.append('</context>')
    return '\n'.join(lines)


def add_translations_to_file(ts_path: str, lang_code: str):
    """Add PresetThumbnail and ShellPanel translations to a .ts file."""
    with open(ts_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if contexts already exist
    if '<name>PresetThumbnail</name>' in content:
        print(f"  PresetThumbnail already exists in {os.path.basename(ts_path)}, skipping")
        return False

    # Find the closing </TS> tag and insert before it
    closing_tag = '</TS>'
    if closing_tag not in content:
        print(f"  Warning: No </TS> tag found in {ts_path}")
        return False

    # Generate new context blocks
    preset_thumbnail_block = generate_context_block(
        "PresetThumbnail", PRESET_THUMBNAIL_TRANSLATIONS, lang_code)
    shell_panel_block = generate_context_block(
        "ShellPanel", SHELL_PANEL_TRANSLATIONS, lang_code)

    # Insert before </TS>
    new_content = content.replace(
        closing_tag,
        f'{preset_thumbnail_block}\n{shell_panel_block}\n{closing_tag}'
    )

    with open(ts_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def main():
    translations_dir = os.path.join(os.path.dirname(__file__), '..', 'translations')

    languages = [
        'zh_CN', 'en_US', 'ru_RU', 'uk_UA', 'de_DE', 'fr_FR',
        'es_ES', 'pt_BR', 'it_IT', 'he_IL', 'ar_SA', 'ja_JP',
        'ko_KR', 'tr_TR'
    ]

    print("Adding UI translations to all language files...")

    for lang in languages:
        ts_file = os.path.join(translations_dir, f'signmaker_{lang}.ts')
        if os.path.exists(ts_file):
            if add_translations_to_file(ts_file, lang):
                print(f"  Added UI translations to signmaker_{lang}.ts")
        else:
            print(f"  Warning: {ts_file} not found")

    print("\nDone! Run 'pyside6-lrelease' to compile .qm files.")


if __name__ == '__main__':
    main()
