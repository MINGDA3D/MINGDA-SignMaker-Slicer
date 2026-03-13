#!/usr/bin/env python3
"""统一翻译所有语言中的常用词"""
import re
from pathlib import Path

# 常用词翻译映射
common_translations = {
    "zh_CN": {
        "OK": "确定",
        "Cancel": "取消",
        "Warning": "警告",
        "Error": "错误",
        "Yes": "是",
        "No": "否",
        "Close": "关闭",
        "Save": "保存",
        "Open": "打开"
    },
    "en_US": {
        "OK": "OK",
        "Cancel": "Cancel",
        "Warning": "Warning",
        "Error": "Error",
        "Yes": "Yes",
        "No": "No",
        "Close": "Close",
        "Save": "Save",
        "Open": "Open"
    },
    "ru_RU": {
        "OK": "ОК",
        "Cancel": "Отмена",
        "Warning": "Предупреждение",
        "Error": "Ошибка",
        "Yes": "Да",
        "No": "Нет",
        "Close": "Закрыть",
        "Save": "Сохранить",
        "Open": "Открыть"
    },
    "uk_UA": {
        "OK": "OK",
        "Cancel": "Скасувати",
        "Warning": "Попередження",
        "Error": "Помилка",
        "Yes": "Так",
        "No": "Ні",
        "Close": "Закрити",
        "Save": "Зберегти",
        "Open": "Відкрити"
    },
    "de_DE": {
        "OK": "OK",
        "Cancel": "Abbrechen",
        "Warning": "Warnung",
        "Error": "Fehler",
        "Yes": "Ja",
        "No": "Nein",
        "Close": "Schließen",
        "Save": "Speichern",
        "Open": "Öffnen"
    },
    "fr_FR": {
        "OK": "OK",
        "Cancel": "Annuler",
        "Warning": "Avertissement",
        "Error": "Erreur",
        "Yes": "Oui",
        "No": "Non",
        "Close": "Fermer",
        "Save": "Enregistrer",
        "Open": "Ouvrir"
    },
    "es_ES": {
        "OK": "Aceptar",
        "Cancel": "Cancelar",
        "Warning": "Advertencia",
        "Error": "Error",
        "Yes": "Sí",
        "No": "No",
        "Close": "Cerrar",
        "Save": "Guardar",
        "Open": "Abrir"
    },
    "pt_BR": {
        "OK": "OK",
        "Cancel": "Cancelar",
        "Warning": "Aviso",
        "Error": "Erro",
        "Yes": "Sim",
        "No": "Não",
        "Close": "Fechar",
        "Save": "Salvar",
        "Open": "Abrir"
    },
    "it_IT": {
        "OK": "OK",
        "Cancel": "Annulla",
        "Warning": "Avviso",
        "Error": "Errore",
        "Yes": "Sì",
        "No": "No",
        "Close": "Chiudi",
        "Save": "Salva",
        "Open": "Apri"
    },
    "he_IL": {
        "OK": "אישור",
        "Cancel": "ביטול",
        "Warning": "אזהרה",
        "Error": "שגיאה",
        "Yes": "כן",
        "No": "לא",
        "Close": "סגור",
        "Save": "שמור",
        "Open": "פתח"
    },
    "ar_SA": {
        "OK": "موافق",
        "Cancel": "إلغاء",
        "Warning": "تحذير",
        "Error": "خطأ",
        "Yes": "نعم",
        "No": "لا",
        "Close": "إغلاق",
        "Save": "حفظ",
        "Open": "فتح"
    },
    "ja_JP": {
        "OK": "OK",
        "Cancel": "キャンセル",
        "Warning": "警告",
        "Error": "エラー",
        "Yes": "はい",
        "No": "いいえ",
        "Close": "閉じる",
        "Save": "保存",
        "Open": "開く"
    },
    "ko_KR": {
        "OK": "확인",
        "Cancel": "취소",
        "Warning": "경고",
        "Error": "오류",
        "Yes": "예",
        "No": "아니오",
        "Close": "닫기",
        "Save": "저장",
        "Open": "열기"
    },
    "tr_TR": {
        "OK": "Tamam",
        "Cancel": "İptal",
        "Warning": "Uyarı",
        "Error": "Hata",
        "Yes": "Evet",
        "No": "Hayır",
        "Close": "Kapat",
        "Save": "Kaydet",
        "Open": "Aç"
    }
}

def update_common_words(lang_code: str):
    """更新常用词翻译"""
    ts_file = Path(__file__).parent.parent / "translations" / f"signmaker_{lang_code}.ts"

    if not ts_file.exists():
        print(f"[SKIP] {lang_code}: File not found")
        return

    trans_map = common_translations.get(lang_code, {})
    if not trans_map:
        print(f"[SKIP] {lang_code}: No translations defined")
        return

    content = ts_file.read_text(encoding="utf-8")
    updated = 0

    for source, target in trans_map.items():
        # 替换所有未翻译或空翻译的常用词
        pattern = rf'(<source>{re.escape(source)}</source>\s*\n\s*)<translation[^>]*>.*?</translation>'

        def replace_func(match):
            nonlocal updated
            updated += 1
            return f'{match.group(1)}<translation>{target}</translation>'

        content = re.sub(pattern, replace_func, content)

    ts_file.write_text(content, encoding="utf-8")
    print(f"[OK] {lang_code}: Updated {updated} entries")

if __name__ == "__main__":
    for lang in common_translations.keys():
        update_common_words(lang)
    print("\nDone! Run 'python tools/update_translations.py compile' to compile.")
