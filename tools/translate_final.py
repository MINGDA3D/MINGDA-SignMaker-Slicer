#!/usr/bin/env python3
"""翻译最后剩余的字符串"""
import re
from pathlib import Path

final_translations = {
    "zh_CN": {
        "Rotation: {angle:.2f}°": "旋转: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "缩放: {px:.1f}% x {py:.1f}%",
        "填充": "填充",
        "实边": "实边",
        "换色": "换色",
        "底面": "底面",
        "顶面": "顶面",
        "图层编辑": "图层编辑",
        "层数编辑": "层数编辑",
        "正": "正",
        "俯": "俯",
        "侧": "侧",
        "透": "透"
    },
    "en_US": {
        "Rotation: {angle:.2f}°": "Rotation: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Scale: {px:.1f}% x {py:.1f}%",
        "填充": "Fill",
        "实边": "Solid Edge",
        "换色": "Color Change",
        "底面": "Bottom Face",
        "顶面": "Top Face",
        "图层编辑": "Layer Edit",
        "层数编辑": "Layer Count Edit",
        "正": "Front",
        "俯": "Top",
        "侧": "Side",
        "透": "Iso"
    },
    "ru_RU": {
        "Rotation: {angle:.2f}°": "Поворот: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Масштаб: {px:.1f}% x {py:.1f}%",
        "填充": "Заполнение",
        "实边": "Сплошной край",
        "换色": "Смена цвета",
        "底面": "Нижняя грань",
        "顶面": "Верхняя грань",
        "图层编辑": "Редактирование слоя",
        "层数编辑": "Редактирование количества слоев",
        "正": "Спереди",
        "俯": "Сверху",
        "侧": "Сбоку",
        "透": "Изометрия"
    },
    "uk_UA": {
        "Rotation: {angle:.2f}°": "Обертання: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Масштаб: {px:.1f}% x {py:.1f}%",
        "填充": "Заповнення",
        "实边": "Суцільний край",
        "换色": "Зміна кольору",
        "底面": "Нижня грань",
        "顶面": "Верхня грань",
        "图层编辑": "Редагування шару",
        "层数编辑": "Редагування кількості шарів",
        "正": "Спереду",
        "俯": "Зверху",
        "侧": "Збоку",
        "透": "Ізометрія"
    },
    "de_DE": {
        "Rotation: {angle:.2f}°": "Drehung: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Skalierung: {px:.1f}% x {py:.1f}%",
        "填充": "Füllung",
        "实边": "Vollkante",
        "换色": "Farbwechsel",
        "底面": "Unterseite",
        "顶面": "Oberseite",
        "图层编辑": "Ebenenbearbeitung",
        "层数编辑": "Ebenenanzahl bearbeiten",
        "正": "Vorne",
        "俯": "Oben",
        "侧": "Seite",
        "透": "Iso"
    },
    "fr_FR": {
        "Rotation: {angle:.2f}°": "Rotation : {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Échelle : {px:.1f}% x {py:.1f}%",
        "填充": "Remplissage",
        "实边": "Bord solide",
        "换色": "Changement de couleur",
        "底面": "Face inférieure",
        "顶面": "Face supérieure",
        "图层编辑": "Édition de couche",
        "层数编辑": "Édition du nombre de couches",
        "正": "Avant",
        "俯": "Dessus",
        "侧": "Côté",
        "透": "Iso"
    },
    "es_ES": {
        "Rotation: {angle:.2f}°": "Rotación: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Escala: {px:.1f}% x {py:.1f}%",
        "填充": "Relleno",
        "实边": "Borde sólido",
        "换色": "Cambio de color",
        "底面": "Cara inferior",
        "顶面": "Cara superior",
        "图层编辑": "Edición de capa",
        "层数编辑": "Edición de número de capas",
        "正": "Frontal",
        "俯": "Superior",
        "侧": "Lateral",
        "透": "Iso"
    },
    "pt_BR": {
        "Rotation: {angle:.2f}°": "Rotação: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Escala: {px:.1f}% x {py:.1f}%",
        "填充": "Preenchimento",
        "实边": "Borda sólida",
        "换色": "Mudança de cor",
        "底面": "Face inferior",
        "顶面": "Face superior",
        "图层编辑": "Edição de camada",
        "层数编辑": "Edição de número de camadas",
        "正": "Frontal",
        "俯": "Superior",
        "侧": "Lateral",
        "透": "Iso"
    },
    "it_IT": {
        "Rotation: {angle:.2f}°": "Rotazione: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Scala: {px:.1f}% x {py:.1f}%",
        "填充": "Riempimento",
        "实边": "Bordo solido",
        "换色": "Cambio colore",
        "底面": "Faccia inferiore",
        "顶面": "Faccia superiore",
        "图层编辑": "Modifica livello",
        "层数编辑": "Modifica numero livelli",
        "正": "Frontale",
        "俯": "Superiore",
        "侧": "Laterale",
        "透": "Iso"
    },
    "he_IL": {
        "Rotation: {angle:.2f}°": "סיבוב: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "קנה מידה: {px:.1f}% x {py:.1f}%",
        "填充": "מילוי",
        "实边": "קצה מוצק",
        "换色": "החלפת צבע",
        "底面": "פנים תחתונות",
        "顶面": "פנים עליונות",
        "图层编辑": "עריכת שכבה",
        "层数编辑": "עריכת מספר שכבות",
        "正": "קדמי",
        "俯": "עליון",
        "侧": "צדדי",
        "透": "איזומטרי"
    },
    "ar_SA": {
        "Rotation: {angle:.2f}°": "الدوران: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "المقياس: {px:.1f}% x {py:.1f}%",
        "填充": "تعبئة",
        "实边": "حافة صلبة",
        "换色": "تغيير اللون",
        "底面": "الوجه السفلي",
        "顶面": "الوجه العلوي",
        "图层编辑": "تحرير الطبقة",
        "层数编辑": "تحرير عدد الطبقات",
        "正": "أمامي",
        "俯": "علوي",
        "侧": "جانبي",
        "透": "متساوي القياس"
    },
    "ja_JP": {
        "Rotation: {angle:.2f}°": "回転: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "スケール: {px:.1f}% x {py:.1f}%",
        "填充": "塗りつぶし",
        "实边": "ソリッドエッジ",
        "换色": "色変更",
        "底面": "底面",
        "顶面": "上面",
        "图层编辑": "レイヤー編集",
        "层数编辑": "レイヤー数編集",
        "正": "正面",
        "俯": "上面",
        "侧": "側面",
        "透": "アイソメ"
    },
    "ko_KR": {
        "Rotation: {angle:.2f}°": "회전: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "크기: {px:.1f}% x {py:.1f}%",
        "填充": "채우기",
        "实边": "솔리드 엣지",
        "换色": "색상 변경",
        "底面": "하단면",
        "顶面": "상단면",
        "图层编辑": "레이어 편집",
        "层数编辑": "레이어 수 편집",
        "正": "정면",
        "俯": "상단",
        "侧": "측면",
        "透": "아이소"
    },
    "tr_TR": {
        "Rotation: {angle:.2f}°": "Döndürme: {angle:.2f}°",
        "Scale: {px:.1f}% x {py:.1f}%": "Ölçek: {px:.1f}% x {py:.1f}%",
        "填充": "Doldurma",
        "实边": "Katı Kenar",
        "换色": "Renk Değişimi",
        "底面": "Alt Yüz",
        "顶面": "Üst Yüz",
        "图层编辑": "Katman Düzenleme",
        "层数编辑": "Katman Sayısı Düzenleme",
        "正": "Ön",
        "俯": "Üst",
        "侧": "Yan",
        "透": "İzo"
    }
}

def update_final_strings(lang_code: str):
    """更新最后剩余的字符串"""
    ts_file = Path(__file__).parent.parent / "translations" / f"signmaker_{lang_code}.ts"
    if not ts_file.exists():
        print(f"[SKIP] {lang_code}: File not found")
        return

    trans_map = final_translations.get(lang_code, {})
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
    for lang in final_translations.keys():
        update_final_strings(lang)
    print("\nDone! Run 'python tools/update_translations.py compile' to compile.")

