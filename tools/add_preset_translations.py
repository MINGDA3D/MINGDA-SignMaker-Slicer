#!/usr/bin/env python
"""
添加异形边预设翻译到所有语言文件
"""

import os
from pathlib import Path

# 异形边预设翻译
PRESET_TRANSLATIONS = {
    # 格式: "English Source": {"zh_CN": "中文", "ru_RU": "俄语", ...}

    # Categories
    "Zigzag": {
        "zh_CN": "锯齿类", "ru_RU": "Зигзаг", "uk_UA": "Зигзаг", "de_DE": "Zickzack",
        "fr_FR": "Zigzag", "es_ES": "Zigzag", "pt_BR": "Zigue-zague", "it_IT": "Zigzag",
        "he_IL": "זיגזג", "ar_SA": "متعرج", "ja_JP": "ジグザグ", "ko_KR": "지그재그", "tr_TR": "Zikzak"
    },
    "Wave": {
        "zh_CN": "波浪类", "ru_RU": "Волна", "uk_UA": "Хвиля", "de_DE": "Welle",
        "fr_FR": "Vague", "es_ES": "Ola", "pt_BR": "Onda", "it_IT": "Onda",
        "he_IL": "גל", "ar_SA": "موجة", "ja_JP": "ウェーブ", "ko_KR": "웨이브", "tr_TR": "Dalga"
    },
    "Arc": {
        "zh_CN": "圆弧类", "ru_RU": "Дуга", "uk_UA": "Дуга", "de_DE": "Bogen",
        "fr_FR": "Arc", "es_ES": "Arco", "pt_BR": "Arco", "it_IT": "Arco",
        "he_IL": "קשת", "ar_SA": "قوس", "ja_JP": "アーク", "ko_KR": "아크", "tr_TR": "Yay"
    },
    "Step": {
        "zh_CN": "台阶类", "ru_RU": "Ступенька", "uk_UA": "Сходинка", "de_DE": "Stufe",
        "fr_FR": "Marche", "es_ES": "Escalón", "pt_BR": "Degrau", "it_IT": "Gradino",
        "he_IL": "מדרגה", "ar_SA": "درجة", "ja_JP": "ステップ", "ko_KR": "계단", "tr_TR": "Basamak"
    },
    "Mixed": {
        "zh_CN": "组合类", "ru_RU": "Смешанный", "uk_UA": "Змішаний", "de_DE": "Gemischt",
        "fr_FR": "Mixte", "es_ES": "Mixto", "pt_BR": "Misto", "it_IT": "Misto",
        "he_IL": "מעורב", "ar_SA": "مختلط", "ja_JP": "ミックス", "ko_KR": "혼합", "tr_TR": "Karma"
    },
    "Bevel": {
        "zh_CN": "斜边类", "ru_RU": "Скос", "uk_UA": "Скіс", "de_DE": "Schräge",
        "fr_FR": "Biseau", "es_ES": "Bisel", "pt_BR": "Chanfro", "it_IT": "Smusso",
        "he_IL": "שיפוע", "ar_SA": "شطبة", "ja_JP": "ベベル", "ko_KR": "베벨", "tr_TR": "Eğim"
    },

    # Zigzag presets
    "4-Tooth Zigzag": {
        "zh_CN": "四锯齿边", "ru_RU": "4-зубчатый зигзаг", "uk_UA": "4-зубчастий зигзаг", "de_DE": "4-Zahn-Zickzack",
        "fr_FR": "Zigzag 4 dents", "es_ES": "Zigzag 4 dientes", "pt_BR": "Zigue-zague 4 dentes", "it_IT": "Zigzag 4 denti",
        "he_IL": "זיגזג 4 שיניים", "ar_SA": "متعرج 4 أسنان", "ja_JP": "4歯ジグザグ", "ko_KR": "4톱니 지그재그", "tr_TR": "4 Dişli Zikzak"
    },
    "4 sharp zigzag teeth, highly decorative": {
        "zh_CN": "4个锐角锯齿，装饰性强", "ru_RU": "4 острых зигзага, высокодекоративный", "uk_UA": "4 гострих зигзаги, високодекоративний",
        "de_DE": "4 scharfe Zickzack-Zähne, hochdekorativ", "fr_FR": "4 dents zigzag aiguës, très décoratif",
        "es_ES": "4 dientes zigzag afilados, muy decorativo", "pt_BR": "4 dentes zigue-zague afiados, altamente decorativo",
        "it_IT": "4 denti zigzag affilati, altamente decorativo", "he_IL": "4 שיני זיגזג חדות, מאוד דקורטיבי",
        "ar_SA": "4 أسنان متعرجة حادة، زخرفية للغاية", "ja_JP": "4つの鋭いジグザグ歯、装飾性が高い",
        "ko_KR": "4개의 날카로운 지그재그 이빨, 매우 장식적", "tr_TR": "4 keskin zikzak diş, oldukça dekoratif"
    },
    "3-Tooth Zigzag": {
        "zh_CN": "三锯齿边", "ru_RU": "3-зубчатый зигзаг", "uk_UA": "3-зубчастий зигзаг", "de_DE": "3-Zahn-Zickzack",
        "fr_FR": "Zigzag 3 dents", "es_ES": "Zigzag 3 dientes", "pt_BR": "Zigue-zague 3 dentes", "it_IT": "Zigzag 3 denti",
        "he_IL": "זיגזג 3 שיניים", "ar_SA": "متعرج 3 أسنان", "ja_JP": "3歯ジグザグ", "ko_KR": "3톱니 지그재그", "tr_TR": "3 Dişli Zikzak"
    },
    "3 zigzag teeth, medium decoration": {
        "zh_CN": "3个锯齿，中等装饰", "ru_RU": "3 зигзага, средний декор", "uk_UA": "3 зигзаги, середній декор",
        "de_DE": "3 Zickzack-Zähne, mittlere Dekoration", "fr_FR": "3 dents zigzag, décoration moyenne",
        "es_ES": "3 dientes zigzag, decoración media", "pt_BR": "3 dentes zigue-zague, decoração média",
        "it_IT": "3 denti zigzag, decorazione media", "he_IL": "3 שיני זיגזג, קישוט בינוני",
        "ar_SA": "3 أسنان متعرجة، زخرفة متوسطة", "ja_JP": "3つのジグザグ歯、中程度の装飾",
        "ko_KR": "3개의 지그재그 이빨, 중간 장식", "tr_TR": "3 zikzak diş, orta dekorasyon"
    },
    "2-Tooth Zigzag": {
        "zh_CN": "双锯齿边", "ru_RU": "2-зубчатый зигзаг", "uk_UA": "2-зубчастий зигзаг", "de_DE": "2-Zahn-Zickzack",
        "fr_FR": "Zigzag 2 dents", "es_ES": "Zigzag 2 dientes", "pt_BR": "Zigue-zague 2 dentes", "it_IT": "Zigzag 2 denti",
        "he_IL": "זיגזג 2 שיניים", "ar_SA": "متعرج 2 أسنان", "ja_JP": "2歯ジグザグ", "ko_KR": "2톱니 지그재그", "tr_TR": "2 Dişli Zikzak"
    },
    "2 zigzag teeth, simple and clean": {
        "zh_CN": "2个锯齿，简洁大方", "ru_RU": "2 зигзага, простой и чистый", "uk_UA": "2 зигзаги, простий і чистий",
        "de_DE": "2 Zickzack-Zähne, einfach und sauber", "fr_FR": "2 dents zigzag, simple et propre",
        "es_ES": "2 dientes zigzag, simple y limpio", "pt_BR": "2 dentes zigue-zague, simples e limpo",
        "it_IT": "2 denti zigzag, semplice e pulito", "he_IL": "2 שיני זיגזג, פשוט ונקי",
        "ar_SA": "2 أسنان متعرجة، بسيط ونظيف", "ja_JP": "2つのジグザグ歯、シンプルでクリーン",
        "ko_KR": "2개의 지그재그 이빨, 단순하고 깔끔", "tr_TR": "2 zikzak diş, basit ve temiz"
    },
    "5-Tooth Zigzag": {
        "zh_CN": "五锯齿边", "ru_RU": "5-зубчатый зигзаг", "uk_UA": "5-зубчастий зигзаг", "de_DE": "5-Zahn-Zickzack",
        "fr_FR": "Zigzag 5 dents", "es_ES": "Zigzag 5 dientes", "pt_BR": "Zigue-zague 5 dentes", "it_IT": "Zigzag 5 denti",
        "he_IL": "זיגזג 5 שיניים", "ar_SA": "متعرج 5 أسنان", "ja_JP": "5歯ジグザグ", "ko_KR": "5톱니 지그재그", "tr_TR": "5 Dişli Zikzak"
    },
    "5 zigzag teeth, complex decoration": {
        "zh_CN": "5个锯齿，复杂装饰", "ru_RU": "5 зигзагов, сложный декор", "uk_UA": "5 зигзагів, складний декор",
        "de_DE": "5 Zickzack-Zähne, komplexe Dekoration", "fr_FR": "5 dents zigzag, décoration complexe",
        "es_ES": "5 dientes zigzag, decoración compleja", "pt_BR": "5 dentes zigue-zague, decoração complexa",
        "it_IT": "5 denti zigzag, decorazione complessa", "he_IL": "5 שיני זיגזג, קישוט מורכב",
        "ar_SA": "5 أسنان متعرجة، زخرفة معقدة", "ja_JP": "5つのジグザグ歯、複雑な装飾",
        "ko_KR": "5개의 지그재그 이빨, 복잡한 장식", "tr_TR": "5 zikzak diş, karmaşık dekorasyon"
    },

    # Wave presets
    "3-Wave": {
        "zh_CN": "三波浪边", "ru_RU": "3 волны", "uk_UA": "3 хвилі", "de_DE": "3 Wellen",
        "fr_FR": "3 vagues", "es_ES": "3 olas", "pt_BR": "3 ondas", "it_IT": "3 onde",
        "he_IL": "3 גלים", "ar_SA": "3 موجات", "ja_JP": "3ウェーブ", "ko_KR": "3웨이브", "tr_TR": "3 Dalga"
    },
    "3 smooth S-shaped waves": {
        "zh_CN": "3个平滑S形波浪", "ru_RU": "3 плавные S-образные волны", "uk_UA": "3 плавні S-подібні хвилі",
        "de_DE": "3 glatte S-förmige Wellen", "fr_FR": "3 vagues en S lisses",
        "es_ES": "3 ondas suaves en forma de S", "pt_BR": "3 ondas suaves em forma de S",
        "it_IT": "3 onde lisce a forma di S", "he_IL": "3 גלים חלקים בצורת S",
        "ar_SA": "3 موجات ناعمة على شكل S", "ja_JP": "3つの滑らかなS字波",
        "ko_KR": "3개의 부드러운 S자형 웨이브", "tr_TR": "3 düzgün S şeklinde dalga"
    },
    "3-Wave B": {
        "zh_CN": "三波浪边B", "ru_RU": "3 волны B", "uk_UA": "3 хвилі B", "de_DE": "3 Wellen B",
        "fr_FR": "3 vagues B", "es_ES": "3 olas B", "pt_BR": "3 ondas B", "it_IT": "3 onde B",
        "he_IL": "3 גלים B", "ar_SA": "3 موجات B", "ja_JP": "3ウェーブB", "ko_KR": "3웨이브 B", "tr_TR": "3 Dalga B"
    },
    "3 smooth waves (variant)": {
        "zh_CN": "3个平滑波浪（变体）", "ru_RU": "3 плавные волны (вариант)", "uk_UA": "3 плавні хвилі (варіант)",
        "de_DE": "3 glatte Wellen (Variante)", "fr_FR": "3 vagues lisses (variante)",
        "es_ES": "3 ondas suaves (variante)", "pt_BR": "3 ondas suaves (variante)",
        "it_IT": "3 onde lisce (variante)", "he_IL": "3 גלים חלקים (גרסה)",
        "ar_SA": "3 موجات ناعمة (نسخة)", "ja_JP": "3つの滑らかな波（バリエーション）",
        "ko_KR": "3개의 부드러운 웨이브 (변형)", "tr_TR": "3 düzgün dalga (varyant)"
    },
    "2-Wave": {
        "zh_CN": "双波浪边", "ru_RU": "2 волны", "uk_UA": "2 хвилі", "de_DE": "2 Wellen",
        "fr_FR": "2 vagues", "es_ES": "2 olas", "pt_BR": "2 ondas", "it_IT": "2 onde",
        "he_IL": "2 גלים", "ar_SA": "2 موجات", "ja_JP": "2ウェーブ", "ko_KR": "2웨이브", "tr_TR": "2 Dalga"
    },
    "2 smooth waves": {
        "zh_CN": "2个平滑波浪", "ru_RU": "2 плавные волны", "uk_UA": "2 плавні хвилі",
        "de_DE": "2 glatte Wellen", "fr_FR": "2 vagues lisses",
        "es_ES": "2 ondas suaves", "pt_BR": "2 ondas suaves",
        "it_IT": "2 onde lisce", "he_IL": "2 גלים חלקים",
        "ar_SA": "2 موجات ناعمة", "ja_JP": "2つの滑らかな波",
        "ko_KR": "2개의 부드러운 웨이브", "tr_TR": "2 düzgün dalga"
    },

    # Arc presets
    "Single Bump": {
        "zh_CN": "单凸起", "ru_RU": "Одиночный выступ", "uk_UA": "Одиночний виступ", "de_DE": "Einzelne Erhebung",
        "fr_FR": "Bosse simple", "es_ES": "Protuberancia simple", "pt_BR": "Saliência simples", "it_IT": "Protuberanza singola",
        "he_IL": "בליטה בודדת", "ar_SA": "نتوء واحد", "ja_JP": "シングルバンプ", "ko_KR": "단일 돌출", "tr_TR": "Tek Tümsek"
    },
    "Single arc bump in the middle": {
        "zh_CN": "中部单个圆弧凸起", "ru_RU": "Одиночный дуговой выступ в центре", "uk_UA": "Одиночний дуговий виступ посередині",
        "de_DE": "Einzelne Bogenwölbung in der Mitte", "fr_FR": "Bosse arquée unique au milieu",
        "es_ES": "Protuberancia de arco única en el medio", "pt_BR": "Saliência de arco única no meio",
        "it_IT": "Protuberanza ad arco singola al centro", "he_IL": "בליטת קשת בודדת באמצע",
        "ar_SA": "نتوء قوس واحد في الوسط", "ja_JP": "中央に単一のアーチ状の突起",
        "ko_KR": "중간에 단일 아크 돌출", "tr_TR": "Ortada tek yay tümsek"
    },
    "Large Arc": {
        "zh_CN": "大圆弧", "ru_RU": "Большая дуга", "uk_UA": "Велика дуга", "de_DE": "Großer Bogen",
        "fr_FR": "Grand arc", "es_ES": "Arco grande", "pt_BR": "Arco grande", "it_IT": "Arco grande",
        "he_IL": "קשת גדולה", "ar_SA": "قوس كبير", "ja_JP": "大きなアーク", "ko_KR": "큰 아크", "tr_TR": "Büyük Yay"
    },
    "Large radius arc transition": {
        "zh_CN": "大弧度圆弧过渡", "ru_RU": "Переход с большим радиусом дуги", "uk_UA": "Перехід з великим радіусом дуги",
        "de_DE": "Bogenübergang mit großem Radius", "fr_FR": "Transition d'arc à grand rayon",
        "es_ES": "Transición de arco de radio grande", "pt_BR": "Transição de arco de raio grande",
        "it_IT": "Transizione ad arco di grande raggio", "he_IL": "מעבר קשת ברדיוס גדול",
        "ar_SA": "انتقال قوس نصف قطر كبير", "ja_JP": "大きな半径のアーク遷移",
        "ko_KR": "큰 반경 아크 전환", "tr_TR": "Büyük yarıçap yay geçişi"
    },
    "Arc with Platform": {
        "zh_CN": "圆弧带平台", "ru_RU": "Дуга с платформой", "uk_UA": "Дуга з платформою", "de_DE": "Bogen mit Plattform",
        "fr_FR": "Arc avec plateforme", "es_ES": "Arco con plataforma", "pt_BR": "Arco com plataforma", "it_IT": "Arco con piattaforma",
        "he_IL": "קשת עם פלטפורמה", "ar_SA": "قوس مع منصة", "ja_JP": "プラットフォーム付きアーク", "ko_KR": "플랫폼이 있는 아크", "tr_TR": "Platformlu Yay"
    },
    "Arc transition with top/bottom platforms": {
        "zh_CN": "圆弧过渡带上下平台", "ru_RU": "Переход дуги с верхней/нижней платформой", "uk_UA": "Перехід дуги з верхньою/нижньою платформою",
        "de_DE": "Bogenübergang mit oberer/unterer Plattform", "fr_FR": "Transition d'arc avec plateformes haut/bas",
        "es_ES": "Transición de arco con plataformas superior/inferior", "pt_BR": "Transição de arco com plataformas superior/inferior",
        "it_IT": "Transizione ad arco con piattaforme superiore/inferiore", "he_IL": "מעבר קשת עם פלטפורמות עליון/תחתון",
        "ar_SA": "انتقال قوس مع منصات علوية/سفلية", "ja_JP": "上下プラットフォーム付きアーク遷移",
        "ko_KR": "상단/하단 플랫폼이 있는 아크 전환", "tr_TR": "Üst/alt platformlu yay geçişi"
    },
    "Arc with Platform B": {
        "zh_CN": "圆弧带平台B", "ru_RU": "Дуга с платформой B", "uk_UA": "Дуга з платформою B", "de_DE": "Bogen mit Plattform B",
        "fr_FR": "Arc avec plateforme B", "es_ES": "Arco con plataforma B", "pt_BR": "Arco com plataforma B", "it_IT": "Arco con piattaforma B",
        "he_IL": "קשת עם פלטפורמה B", "ar_SA": "قوس مع منصة B", "ja_JP": "プラットフォーム付きアークB", "ko_KR": "플랫폼이 있는 아크 B", "tr_TR": "Platformlu Yay B"
    },
    "Arc with platform (variant)": {
        "zh_CN": "圆弧过渡带平台（变体）", "ru_RU": "Дуга с платформой (вариант)", "uk_UA": "Дуга з платформою (варіант)",
        "de_DE": "Bogen mit Plattform (Variante)", "fr_FR": "Arc avec plateforme (variante)",
        "es_ES": "Arco con plataforma (variante)", "pt_BR": "Arco com plataforma (variante)",
        "it_IT": "Arco con piattaforma (variante)", "he_IL": "קשת עם פלטפורמה (גרסה)",
        "ar_SA": "قوس مع منصة (نسخة)", "ja_JP": "プラットフォーム付きアーク（バリエーション）",
        "ko_KR": "플랫폼이 있는 아크 (변형)", "tr_TR": "Platformlu yay (varyant)"
    },

    # Step presets
    "Small Step": {
        "zh_CN": "小台阶", "ru_RU": "Маленькая ступенька", "uk_UA": "Маленька сходинка", "de_DE": "Kleine Stufe",
        "fr_FR": "Petite marche", "es_ES": "Escalón pequeño", "pt_BR": "Degrau pequeno", "it_IT": "Piccolo gradino",
        "he_IL": "מדרגה קטנה", "ar_SA": "درجة صغيرة", "ja_JP": "小さなステップ", "ko_KR": "작은 계단", "tr_TR": "Küçük Basamak"
    },
    "Single small step": {
        "zh_CN": "单级小台阶", "ru_RU": "Одна маленькая ступенька", "uk_UA": "Одна маленька сходинка",
        "de_DE": "Eine kleine Stufe", "fr_FR": "Une petite marche",
        "es_ES": "Un escalón pequeño", "pt_BR": "Um degrau pequeno",
        "it_IT": "Un piccolo gradino", "he_IL": "מדרגה קטנה אחת",
        "ar_SA": "درجة صغيرة واحدة", "ja_JP": "1つの小さなステップ",
        "ko_KR": "하나의 작은 계단", "tr_TR": "Tek küçük basamak"
    },
    "Double Step": {
        "zh_CN": "双台阶", "ru_RU": "Двойная ступенька", "uk_UA": "Подвійна сходинка", "de_DE": "Doppelstufe",
        "fr_FR": "Double marche", "es_ES": "Escalón doble", "pt_BR": "Degrau duplo", "it_IT": "Doppio gradino",
        "he_IL": "מדרגה כפולה", "ar_SA": "درجة مزدوجة", "ja_JP": "ダブルステップ", "ko_KR": "이중 계단", "tr_TR": "Çift Basamak"
    },
    "Two-level step": {
        "zh_CN": "双级台阶", "ru_RU": "Двухуровневая ступенька", "uk_UA": "Дворівнева сходинка",
        "de_DE": "Zweistufige Stufe", "fr_FR": "Marche à deux niveaux",
        "es_ES": "Escalón de dos niveles", "pt_BR": "Degrau de dois níveis",
        "it_IT": "Gradino a due livelli", "he_IL": "מדרגה דו-רמתית",
        "ar_SA": "درجة بمستويين", "ja_JP": "2段ステップ",
        "ko_KR": "2단 계단", "tr_TR": "İki seviyeli basamak"
    },

    # Mixed presets
    "Step + Arc": {
        "zh_CN": "台阶+圆弧", "ru_RU": "Ступенька + дуга", "uk_UA": "Сходинка + дуга", "de_DE": "Stufe + Bogen",
        "fr_FR": "Marche + arc", "es_ES": "Escalón + arco", "pt_BR": "Degrau + arco", "it_IT": "Gradino + arco",
        "he_IL": "מדרגה + קשת", "ar_SA": "درجة + قوس", "ja_JP": "ステップ + アーク", "ko_KR": "계단 + 아크", "tr_TR": "Basamak + Yay"
    },
    "Combination of step and arc": {
        "zh_CN": "台阶与圆弧组合", "ru_RU": "Комбинация ступеньки и дуги", "uk_UA": "Комбінація сходинки та дуги",
        "de_DE": "Kombination aus Stufe und Bogen", "fr_FR": "Combinaison de marche et d'arc",
        "es_ES": "Combinación de escalón y arco", "pt_BR": "Combinação de degrau e arco",
        "it_IT": "Combinazione di gradino e arco", "he_IL": "שילוב של מדרגה וקשת",
        "ar_SA": "مزيج من الدرجة والقوس", "ja_JP": "ステップとアークの組み合わせ",
        "ko_KR": "계단과 아크의 조합", "tr_TR": "Basamak ve yay kombinasyonu"
    },
    "Complex Mixed": {
        "zh_CN": "复杂组合", "ru_RU": "Сложная комбинация", "uk_UA": "Складна комбінація", "de_DE": "Komplexe Mischung",
        "fr_FR": "Mixte complexe", "es_ES": "Mixto complejo", "pt_BR": "Misto complexo", "it_IT": "Misto complesso",
        "he_IL": "מעורב מורכב", "ar_SA": "مختلط معقد", "ja_JP": "複合ミックス", "ko_KR": "복합 혼합", "tr_TR": "Karmaşık Karma"
    },
    "Double arc + step complex combination": {
        "zh_CN": "双圆弧+台阶复杂组合", "ru_RU": "Двойная дуга + ступенька, сложная комбинация", "uk_UA": "Подвійна дуга + сходинка, складна комбінація",
        "de_DE": "Doppelbogen + Stufe, komplexe Kombination", "fr_FR": "Double arc + marche, combinaison complexe",
        "es_ES": "Doble arco + escalón, combinación compleja", "pt_BR": "Arco duplo + degrau, combinação complexa",
        "it_IT": "Doppio arco + gradino, combinazione complessa", "he_IL": "קשת כפולה + מדרגה, שילוב מורכב",
        "ar_SA": "قوس مزدوج + درجة، مزيج معقد", "ja_JP": "ダブルアーク + ステップの複雑な組み合わせ",
        "ko_KR": "이중 아크 + 계단 복합 조합", "tr_TR": "Çift yay + basamak karmaşık kombinasyon"
    },

    # Bevel presets
    "Simple Bevel": {
        "zh_CN": "简单斜边", "ru_RU": "Простой скос", "uk_UA": "Простий скіс", "de_DE": "Einfache Schräge",
        "fr_FR": "Biseau simple", "es_ES": "Bisel simple", "pt_BR": "Chanfro simples", "it_IT": "Smusso semplice",
        "he_IL": "שיפוע פשוט", "ar_SA": "شطبة بسيطة", "ja_JP": "シンプルベベル", "ko_KR": "단순 베벨", "tr_TR": "Basit Eğim"
    },
    "Linear bevel transition": {
        "zh_CN": "线性斜边过渡", "ru_RU": "Линейный скос", "uk_UA": "Лінійний скіс",
        "de_DE": "Linearer Schrägenübergang", "fr_FR": "Transition de biseau linéaire",
        "es_ES": "Transición de bisel lineal", "pt_BR": "Transição de chanfro linear",
        "it_IT": "Transizione smusso lineare", "he_IL": "מעבר שיפוע לינארי",
        "ar_SA": "انتقال شطبة خطي", "ja_JP": "リニアベベル遷移",
        "ko_KR": "선형 베벨 전환", "tr_TR": "Doğrusal eğim geçişi"
    },
    "Large Bevel": {
        "zh_CN": "大斜边", "ru_RU": "Большой скос", "uk_UA": "Великий скіс", "de_DE": "Große Schräge",
        "fr_FR": "Grand biseau", "es_ES": "Bisel grande", "pt_BR": "Chanfro grande", "it_IT": "Smusso grande",
        "he_IL": "שיפוע גדול", "ar_SA": "شطبة كبيرة", "ja_JP": "大きなベベル", "ko_KR": "큰 베벨", "tr_TR": "Büyük Eğim"
    },
    "Large angle bevel transition": {
        "zh_CN": "大角度斜边过渡", "ru_RU": "Скос с большим углом", "uk_UA": "Скіс з великим кутом",
        "de_DE": "Großwinkel-Schrägenübergang", "fr_FR": "Transition de biseau à grand angle",
        "es_ES": "Transición de bisel de ángulo grande", "pt_BR": "Transição de chanfro de ângulo grande",
        "it_IT": "Transizione smusso ad angolo grande", "he_IL": "מעבר שיפוע בזווית גדולה",
        "ar_SA": "انتقال شطبة بزاوية كبيرة", "ja_JP": "大角度ベベル遷移",
        "ko_KR": "큰 각도 베벨 전환", "tr_TR": "Büyük açılı eğim geçişi"
    },
    "Steep Bevel": {
        "zh_CN": "陡斜边", "ru_RU": "Крутой скос", "uk_UA": "Крутий скіс", "de_DE": "Steile Schräge",
        "fr_FR": "Biseau raide", "es_ES": "Bisel empinado", "pt_BR": "Chanfro íngreme", "it_IT": "Smusso ripido",
        "he_IL": "שיפוע תלול", "ar_SA": "شطبة شديدة", "ja_JP": "急なベベル", "ko_KR": "급한 베벨", "tr_TR": "Dik Eğim"
    },
    "Steep bevel (large width)": {
        "zh_CN": "陡峭斜边（大宽度）", "ru_RU": "Крутой скос (большая ширина)", "uk_UA": "Крутий скіс (велика ширина)",
        "de_DE": "Steile Schräge (große Breite)", "fr_FR": "Biseau raide (grande largeur)",
        "es_ES": "Bisel empinado (ancho grande)", "pt_BR": "Chanfro íngreme (largura grande)",
        "it_IT": "Smusso ripido (larghezza grande)", "he_IL": "שיפוע תלול (רוחב גדול)",
        "ar_SA": "شطبة شديدة (عرض كبير)", "ja_JP": "急なベベル（大幅）",
        "ko_KR": "급한 베벨 (큰 폭)", "tr_TR": "Dik eğim (geniş genişlik)"
    },
}

def generate_context_block(lang_code: str) -> str:
    """Generate translation context block for EdgePresets"""
    lines = ['<context>', '    <name>EdgePresets</name>']

    for source, translations in PRESET_TRANSLATIONS.items():
        translation = translations.get(lang_code, source)  # Fallback to English
        lines.append('    <message>')
        lines.append(f'        <source>{source}</source>')
        lines.append(f'        <translation>{translation}</translation>')
        lines.append('    </message>')

    lines.append('</context>')
    return '\n'.join(lines)

def update_translation_file(ts_path: Path, lang_code: str):
    """Add EdgePresets translations to a .ts file"""
    content = ts_path.read_text(encoding='utf-8')

    # Check if EdgePresets context already exists
    if '<name>EdgePresets</name>' in content:
        print(f"  EdgePresets already exists in {ts_path.name}, skipping...")
        return False

    # Find the closing </TS> tag and insert before it
    context_block = generate_context_block(lang_code)
    new_content = content.replace('</TS>', f'{context_block}\n</TS>')

    ts_path.write_text(new_content, encoding='utf-8')
    print(f"  Added EdgePresets to {ts_path.name}")
    return True

def main():
    translations_dir = Path(__file__).parent.parent / 'translations'

    # Language codes mapping
    lang_files = {
        'zh_CN': 'signmaker_zh_CN.ts',
        'en_US': 'signmaker_en_US.ts',
        'ru_RU': 'signmaker_ru_RU.ts',
        'uk_UA': 'signmaker_uk_UA.ts',
        'de_DE': 'signmaker_de_DE.ts',
        'fr_FR': 'signmaker_fr_FR.ts',
        'es_ES': 'signmaker_es_ES.ts',
        'pt_BR': 'signmaker_pt_BR.ts',
        'it_IT': 'signmaker_it_IT.ts',
        'he_IL': 'signmaker_he_IL.ts',
        'ar_SA': 'signmaker_ar_SA.ts',
        'ja_JP': 'signmaker_ja_JP.ts',
        'ko_KR': 'signmaker_ko_KR.ts',
        'tr_TR': 'signmaker_tr_TR.ts',
    }

    print("Adding EdgePresets translations to all language files...")

    for lang_code, filename in lang_files.items():
        ts_path = translations_dir / filename
        if ts_path.exists():
            update_translation_file(ts_path, lang_code)
        else:
            print(f"  Warning: {filename} not found")

    print("\nDone! Run 'pyside6-lrelease' to compile .qm files.")

if __name__ == '__main__':
    main()
