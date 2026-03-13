#!/usr/bin/env python3
"""翻译剩余的界面元素"""
import re
from pathlib import Path

# 界面元素翻译映射
ui_translations = {
    "zh_CN": {
        "Delete": "删除",
        "Mirror": "镜像",
        "Mirror X": "X轴镜像",
        "Mirror Y": "Y轴镜像",
        "Select All": "全选",
        "Fit View": "适应视图",
        "Reset View": "重置视图",
        "Text": "文字",
        "Export Baseplate DXF...": "导出底板DXF...",
        "Export Panel DXF...": "导出面板DXF...",
        "Loaded saved parameters": "已加载保存的参数",
        "外壳": "外壳",
        "内壳": "内壳"
    },
    "en_US": {
        "Delete": "Delete",
        "Mirror": "Mirror",
        "Mirror X": "Mirror X",
        "Mirror Y": "Mirror Y",
        "Select All": "Select All",
        "Fit View": "Fit View",
        "Reset View": "Reset View",
        "Text": "Text",
        "Export Baseplate DXF...": "Export Baseplate DXF...",
        "Export Panel DXF...": "Export Panel DXF...",
        "Loaded saved parameters": "Loaded saved parameters",
        "外壳": "Outer Shell",
        "内壳": "Inner Shell"
    },
    "ru_RU": {
        "Delete": "Удалить",
        "Mirror": "Отразить",
        "Mirror X": "Отразить по X",
        "Mirror Y": "Отразить по Y",
        "Select All": "Выбрать все",
        "Fit View": "Вписать в окно",
        "Reset View": "Сбросить вид",
        "Text": "Текст",
        "Export Baseplate DXF...": "Экспорт DXF основания...",
        "Export Panel DXF...": "Экспорт DXF панели...",
        "Loaded saved parameters": "Загружены сохраненные параметры",
        "外壳": "Внешняя оболочка",
        "内壳": "Внутренняя оболочка"
    },
    "uk_UA": {
        "Delete": "Видалити",
        "Mirror": "Відзеркалити",
        "Mirror X": "Відзеркалити по X",
        "Mirror Y": "Відзеркалити по Y",
        "Select All": "Вибрати все",
        "Fit View": "Вмістити у вікно",
        "Reset View": "Скинути вигляд",
        "Text": "Текст",
        "Export Baseplate DXF...": "Експорт DXF основи...",
        "Export Panel DXF...": "Експорт DXF панелі...",
        "Loaded saved parameters": "Завантажено збережені параметри",
        "外壳": "Зовнішня оболонка",
        "内壳": "Внутрішня оболонка"
    },
    "de_DE": {
        "Delete": "Löschen",
        "Mirror": "Spiegeln",
        "Mirror X": "X-Achse spiegeln",
        "Mirror Y": "Y-Achse spiegeln",
        "Select All": "Alles auswählen",
        "Fit View": "Ansicht anpassen",
        "Reset View": "Ansicht zurücksetzen",
        "Text": "Text",
        "Export Baseplate DXF...": "Grundplatte DXF exportieren...",
        "Export Panel DXF...": "Panel DXF exportieren...",
        "Loaded saved parameters": "Gespeicherte Parameter geladen",
        "外壳": "Äußere Schale",
        "内壳": "Innere Schale"
    },
    "fr_FR": {
        "Delete": "Supprimer",
        "Mirror": "Miroir",
        "Mirror X": "Miroir X",
        "Mirror Y": "Miroir Y",
        "Select All": "Tout sélectionner",
        "Fit View": "Ajuster la vue",
        "Reset View": "Réinitialiser la vue",
        "Text": "Texte",
        "Export Baseplate DXF...": "Exporter DXF de base...",
        "Export Panel DXF...": "Exporter DXF de panneau...",
        "Loaded saved parameters": "Paramètres sauvegardés chargés",
        "外壳": "Coque extérieure",
        "内壳": "Coque intérieure"
    },
    "es_ES": {
        "Delete": "Eliminar",
        "Mirror": "Reflejar",
        "Mirror X": "Reflejar X",
        "Mirror Y": "Reflejar Y",
        "Select All": "Seleccionar todo",
        "Fit View": "Ajustar vista",
        "Reset View": "Restablecer vista",
        "Text": "Texto",
        "Export Baseplate DXF...": "Exportar DXF de base...",
        "Export Panel DXF...": "Exportar DXF de panel...",
        "Loaded saved parameters": "Parámetros guardados cargados",
        "外壳": "Carcasa exterior",
        "内壳": "Carcasa interior"
    },
    "pt_BR": {
        "Delete": "Excluir",
        "Mirror": "Espelhar",
        "Mirror X": "Espelhar X",
        "Mirror Y": "Espelhar Y",
        "Select All": "Selecionar tudo",
        "Fit View": "Ajustar visualização",
        "Reset View": "Redefinir visualização",
        "Text": "Texto",
        "Export Baseplate DXF...": "Exportar DXF da base...",
        "Export Panel DXF...": "Exportar DXF do painel...",
        "Loaded saved parameters": "Parâmetros salvos carregados",
        "外壳": "Carcaça externa",
        "内壳": "Carcaça interna"
    },
    "it_IT": {
        "Delete": "Elimina",
        "Mirror": "Specchia",
        "Mirror X": "Specchia X",
        "Mirror Y": "Specchia Y",
        "Select All": "Seleziona tutto",
        "Fit View": "Adatta vista",
        "Reset View": "Ripristina vista",
        "Text": "Testo",
        "Export Baseplate DXF...": "Esporta DXF base...",
        "Export Panel DXF...": "Esporta DXF pannello...",
        "Loaded saved parameters": "Parametri salvati caricati",
        "外壳": "Guscio esterno",
        "内壳": "Guscio interno"
    },
    "he_IL": {
        "Delete": "מחק",
        "Mirror": "שיקוף",
        "Mirror X": "שיקוף X",
        "Mirror Y": "שיקוף Y",
        "Select All": "בחר הכל",
        "Fit View": "התאם תצוגה",
        "Reset View": "אפס תצוגה",
        "Text": "טקסט",
        "Export Baseplate DXF...": "ייצא DXF בסיס...",
        "Export Panel DXF...": "ייצא DXF פאנל...",
        "Loaded saved parameters": "פרמטרים שמורים נטענו",
        "外壳": "מעטפת חיצונית",
        "内壳": "מעטפת פנימית"
    },
    "ar_SA": {
        "Delete": "حذف",
        "Mirror": "انعكاس",
        "Mirror X": "انعكاس X",
        "Mirror Y": "انعكاس Y",
        "Select All": "تحديد الكل",
        "Fit View": "ملاءمة العرض",
        "Reset View": "إعادة تعيين العرض",
        "Text": "نص",
        "Export Baseplate DXF...": "تصدير DXF القاعدة...",
        "Export Panel DXF...": "تصدير DXF اللوحة...",
        "Loaded saved parameters": "تم تحميل المعلمات المحفوظة",
        "外壳": "الغلاف الخارجي",
        "内壳": "الغلاف الداخلي"
    },
    "ja_JP": {
        "Delete": "削除",
        "Mirror": "ミラー",
        "Mirror X": "X軸ミラー",
        "Mirror Y": "Y軸ミラー",
        "Select All": "すべて選択",
        "Fit View": "ビューに合わせる",
        "Reset View": "ビューをリセット",
        "Text": "テキスト",
        "Export Baseplate DXF...": "ベースプレートDXFをエクスポート...",
        "Export Panel DXF...": "パネルDXFをエクスポート...",
        "Loaded saved parameters": "保存されたパラメータを読み込みました",
        "外壳": "外殻",
        "内壳": "内殻"
    },
    "ko_KR": {
        "Delete": "삭제",
        "Mirror": "미러",
        "Mirror X": "X축 미러",
        "Mirror Y": "Y축 미러",
        "Select All": "모두 선택",
        "Fit View": "뷰 맞춤",
        "Reset View": "뷰 재설정",
        "Text": "텍스트",
        "Export Baseplate DXF...": "베이스플레이트 DXF 내보내기...",
        "Export Panel DXF...": "패널 DXF 내보내기...",
        "Loaded saved parameters": "저장된 매개변수를 불러왔습니다",
        "外壳": "외부 쉘",
        "内壳": "내부 쉘"
    },
    "tr_TR": {
        "Delete": "Sil",
        "Mirror": "Aynala",
        "Mirror X": "X Ekseninde Aynala",
        "Mirror Y": "Y Ekseninde Aynala",
        "Select All": "Tümünü Seç",
        "Fit View": "Görünümü Sığdır",
        "Reset View": "Görünümü Sıfırla",
        "Text": "Metin",
        "Export Baseplate DXF...": "Taban Plakası DXF Dışa Aktar...",
        "Export Panel DXF...": "Panel DXF Dışa Aktar...",
        "Loaded saved parameters": "Kaydedilmiş parametreler yüklendi",
        "外壳": "Dış Kabuk",
        "内壳": "İç Kabuk"
    }
}

def update_ui_elements(lang_code: str):
    """更新界面元素翻译"""
    ts_file = Path(__file__).parent.parent / "translations" / f"signmaker_{lang_code}.ts"
    if not ts_file.exists():
        print(f"[SKIP] {lang_code}: File not found")
        return

    trans_map = ui_translations.get(lang_code, {})
    if not trans_map:
        print(f"[SKIP] {lang_code}: No translations defined")
        return

    content = ts_file.read_text(encoding="utf-8")
    updated = 0

    for source, target in trans_map.items():
        pattern = rf'(<source>{re.escape(source)}</source>\s*\n\s*)<translation[^>]*>.*?</translation>'
        def replace_func(match):
            nonlocal updated
            updated += 1
            return f'{match.group(1)}<translation>{target}</translation>'
        content = re.sub(pattern, replace_func, content)

    ts_file.write_text(content, encoding="utf-8")
    print(f"[OK] {lang_code}: Updated {updated} entries")

if __name__ == "__main__":
    for lang in ui_translations.keys():
        update_ui_elements(lang)
    print("\nDone! Run 'python tools/update_translations.py compile' to compile.")

