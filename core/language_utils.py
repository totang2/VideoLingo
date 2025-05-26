def normalize_language(lang):
    """将语言代码或描述标准化为语言代码"""
    # 语言代码映射
    lang_map = {
        '简体中文': 'zh',
        '繁體中文': 'zh',
        '中文': 'zh',
        'chinese': 'zh',
        'english': 'en',
        '英文': 'en',
        '英语': 'en',
        'spanish': 'es',
        '西班牙语': 'es',
        'russian': 'ru',
        '俄语': 'ru',
        'french': 'fr',
        '法语': 'fr',
        'german': 'de',
        '德语': 'de',
        'italian': 'it',
        '意大利语': 'it',
        'japanese': 'ja',
        '日语': 'ja',
        'korean': 'ko',
        '韩语': 'ko'
    }
    # 转换为小写并去除空格
    lang = lang.lower().strip()
    # 返回映射的语言代码，如果没有映射则返回原值
    return lang_map.get(lang, lang) 