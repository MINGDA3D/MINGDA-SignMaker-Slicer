#!/usr/bin/env python3
"""批量翻译 TextDialog 的字符串到所有语言"""
import re
from pathlib import Path

# 翻译映射
translations = {
    "en_US": {
        "Generate Text": "Generate Text",
        "Font:": "Font:",
        "Text:": "Text:",
        "Font Size (mm):": "Font Size (mm):",
        "Character Spacing (mm):": "Character Spacing (mm):",
        "Cancel": "Cancel",
        "OK": "OK",
        "Warning": "Warning",
        "Please enter text": "Please enter text",
        "Font not found": "Font not found",
        "Error": "Error"
    },
    "ru_RU": {
        "Generate Text": "Создать текст",
        "Font:": "Шрифт:",
        "Text:": "Текст:",
        "Font Size (mm):": "Размер шрифта (мм):",
        "Character Spacing (mm):": "Межсимвольный интервал (мм):",
        "Cancel": "Отмена",
        "OK": "ОК",
        "Warning": "Предупреждение",
        "Please enter text": "Пожалуйста, введите текст",
        "Font not found": "Шрифт не найден",
        "Error": "Ошибка"
    },
    "uk_UA": {
        "Generate Text": "Створити текст",
        "Font:": "Шрифт:",
        "Text:": "Текст:",
        "Font Size (mm):": "Розмір шрифту (мм):",
        "Character Spacing (mm):": "Міжсимвольний інтервал (мм):",
        "Cancel": "Скасувати",
        "OK": "OK",
        "Warning": "Попередження",
        "Please enter text": "Будь ласка, введіть текст",
        "Font not found": "Шрифт не знайдено",
        "Error": "Помилка"
    },
    "de_DE": {
        "Generate Text": "Text generieren",
        "Font:": "Schriftart:",
        "Text:": "Text:",
        "Font Size (mm):": "Schriftgröße (mm):",
        "Character Spacing (mm):": "Zeichenabstand (mm):",
        "Cancel": "Abbrechen",
        "OK": "OK",
        "Warning": "Warnung",
        "Please enter text": "Bitte Text eingeben",
        "Font not found": "Schriftart nicht gefunden",
        "Error": "Fehler"
    },
    "fr_FR": {
        "Generate Text": "Générer du texte",
        "Font:": "Police :",
        "Text:": "Texte :",
        "Font Size (mm):": "Taille de police (mm) :",
        "Character Spacing (mm):": "Espacement des caractères (mm) :",
        "Cancel": "Annuler",
        "OK": "OK",
        "Warning": "Avertissement",
        "Please enter text": "Veuillez saisir du texte",
        "Font not found": "Police introuvable",
        "Error": "Erreur"
    },
    "es_ES": {
        "Generate Text": "Generar texto",
        "Font:": "Fuente:",
        "Text:": "Texto:",
        "Font Size (mm):": "Tamaño de fuente (mm):",
        "Character Spacing (mm):": "Espaciado de caracteres (mm):",
        "Cancel": "Cancelar",
        "OK": "Aceptar",
        "Warning": "Advertencia",
        "Please enter text": "Por favor, ingrese texto",
        "Font not found": "Fuente no encontrada",
        "Error": "Error"
    },
    "pt_BR": {
        "Generate Text": "Gerar texto",
        "Font:": "Fonte:",
        "Text:": "Texto:",
        "Font Size (mm):": "Tamanho da fonte (mm):",
        "Character Spacing (mm):": "Espaçamento de caracteres (mm):",
        "Cancel": "Cancelar",
        "OK": "OK",
        "Warning": "Aviso",
        "Please enter text": "Por favor, insira o texto",
        "Font not found": "Fonte não encontrada",
        "Error": "Erro"
    },
    "it_IT": {
        "Generate Text": "Genera testo",
        "Font:": "Carattere:",
        "Text:": "Testo:",
        "Font Size (mm):": "Dimensione carattere (mm):",
        "Character Spacing (mm):": "Spaziatura caratteri (mm):",
        "Cancel": "Annulla",
        "OK": "OK",
        "Warning": "Avviso",
        "Please enter text": "Inserisci il testo",
        "Font not found": "Carattere non trovato",
        "Error": "Errore"
    },
    "he_IL": {
        "Generate Text": "צור טקסט",
        "Font:": "גופן:",
        "Text:": "טקסט:",
        "Font Size (mm):": "גודל גופן (מ\"מ):",
        "Character Spacing (mm):": "מרווח תווים (מ\"מ):",
        "Cancel": "ביטול",
        "OK": "אישור",
        "Warning": "אזהרה",
        "Please enter text": "נא להזין טקסט",
        "Font not found": "הגופן לא נמצא",
        "Error": "שגיאה"
    },
    "ar_SA": {
        "Generate Text": "إنشاء نص",
        "Font:": "الخط:",
        "Text:": "النص:",
        "Font Size (mm):": "حجم الخط (مم):",
        "Character Spacing (mm):": "تباعد الأحرف (مم):",
        "Cancel": "إلغاء",
        "OK": "موافق",
        "Warning": "تحذير",
        "Please enter text": "الرجاء إدخال النص",
        "Font not found": "الخط غير موجود",
        "Error": "خطأ"
    },
    "ja_JP": {
        "Generate Text": "テキストを生成",
        "Font:": "フォント：",
        "Text:": "テキスト：",
        "Font Size (mm):": "フォントサイズ (mm)：",
        "Character Spacing (mm):": "文字間隔 (mm)：",
        "Cancel": "キャンセル",
        "OK": "OK",
        "Warning": "警告",
        "Please enter text": "テキストを入力してください",
        "Font not found": "フォントが見つかりません",
        "Error": "エラー"
    },
    "ko_KR": {
        "Generate Text": "텍스트 생성",
        "Font:": "글꼴:",
        "Text:": "텍스트:",
        "Font Size (mm):": "글꼴 크기 (mm):",
        "Character Spacing (mm):": "문자 간격 (mm):",
        "Cancel": "취소",
        "OK": "확인",
        "Warning": "경고",
        "Please enter text": "텍스트를 입력하세요",
        "Font not found": "글꼴을 찾을 수 없습니다",
        "Error": "오류"
    },
    "tr_TR": {
        "Generate Text": "Metin Oluştur",
        "Font:": "Yazı Tipi:",
        "Text:": "Metin:",
        "Font Size (mm):": "Yazı Boyutu (mm):",
        "Character Spacing (mm):": "Karakter Aralığı (mm):",
        "Cancel": "İptal",
        "OK": "Tamam",
        "Warning": "Uyarı",
        "Please enter text": "Lütfen metin girin",
        "Font not found": "Yazı tipi bulunamadı",
        "Error": "Hata"
    }
}

def update_translation_file(lang_code: str):
    """更新指定语言的翻译文件"""
    ts_file = Path(__file__).parent.parent / "translations" / f"signmaker_{lang_code}.ts"

    if not ts_file.exists():
        print(f"[SKIP] {lang_code}: File not found")
        return

    content = ts_file.read_text(encoding="utf-8")
    trans_map = translations.get(lang_code, {})

    if not trans_map:
        print(f"[SKIP] {lang_code}: No translations defined")
        return

    # 替换每个翻译
    for source, target in trans_map.items():
        # 匹配模式：<source>SOURCE</source>\n        <translation type="unfinished"></translation>
        pattern = rf'(<source>{re.escape(source)}</source>\s*\n\s*)<translation type="unfinished">.*?</translation>'
        replacement = rf'\1<translation>{target}</translation>'
        content = re.sub(pattern, replacement, content)

    ts_file.write_text(content, encoding="utf-8")
    print(f"[OK] {lang_code}: Updated")

if __name__ == "__main__":
    for lang in translations.keys():
        update_translation_file(lang)
    print("\nDone! Run 'python tools/update_translations.py compile' to compile.")
