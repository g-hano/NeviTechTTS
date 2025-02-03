POLLY_SAMPLE_RATE = 16000
POLLY_LANGUAGE_NAMES = {
    'arb': 'Polly Arabic',
    'ar-AE': 'Polly Arabic (Gulf)',
    'ca-ES': 'Polly Catalan',
    'yue-CN': 'Polly Chinese (Cantonese)',
    'cmn-CN': 'Polly Chinese (Mandarin)',
    'cs-CZ': 'Polly Czech',
    'da-DK': 'Polly Danish',
    'nl-BE': 'Polly Dutch (Belgian)',
    'nl-NL': 'Polly Dutch',
    'en-AU': 'Polly English (Australian)',
    'en-GB': 'Polly English (British)',
    'en-IN': 'Polly English (Indian)',
    'en-NZ': 'Polly English (New Zealand)',
    'en-ZA': 'Polly English (South African)',
    'en-US': 'Polly English (US)',
    'en-GB-WLS': 'Polly English (Welsh)',
    'fi-FI': 'Polly Finnish',
    'fr-FR': 'Polly French',
    'fr-BE': 'Polly French (Belgian)',
    'fr-CA': 'Polly French (Canadian)',
    'hi-IN': 'Polly Hindi',
    'de-DE': 'Polly German',
    'de-AT': 'Polly German (Austrian)',
    'de-CH': 'Polly German (Swiss standard)',
    'is-IS': 'Polly Icelandic',
    'it-IT': 'Polly Italian',
    'ja-JP': 'Polly Japanese',
    'ko-KR': 'Polly Korean',
    'nb-NO': 'Polly Norwegian',
    'pl-PL': 'Polly Polish',
    'pt-BR': 'Polly Portuguese (Brazilian)',
    'pt-PT': 'Polly Portuguese (European)',
    'ro-RO': 'Polly Romanian',
    'ru-RU': 'Polly Russian',
    'es-ES': 'Polly Spanish (Spain)',
    'es-MX': 'Polly Spanish (Mexican)',
    'es-US': 'Polly Spanish (US)',
    'sv-SE': 'Polly Swedish',
    'tr-TR': 'Polly Turkish',
    'cy-GB': 'Polly Welsh'
}

XTTS_SAMPLE_RATE = 24000
XTTS_LANGUAGE_NAMES = {
    "en": "English",
    "sp": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "pl": "Polish",
    "tr": "Turkish",
    "ru": "Russian",
    "nl": "Dutch",
    "cs": "Czech",
    "ar": "Arabic",
    "zh-cn": "Chinese",
    "ja": "Japanese",
    "hu": "Hungarian",
    "ko": "Korean",
    "hi": "Hindi"    
}

KOKORO_VOICE_CHOICES = [
    # US English (a) Voices
    ("KOKORO US Fenrir", "am_fenrir", "m"),
    ("KOKORO US Nicole", "af_nicole", "f"),
    ("KOKORO US Jessica", "af_jessica", "f"),
    ("KOKORO US River", "af_river", "f"),
    ("KOKORO US Eric", "am_eric", "m"),
    ("KOKORO US Adam", "am_adam", "m"),
    ("KOKORO US Alloy", "af_alloy", "f"),
    ("KOKORO US Heart", "af_heart", "f"),
    ("KOKORO US Onyx", "am_onyx", "m"),
    ("KOKORO US Bella", "af_bella", "f"),
    ("KOKORO US Aoede", "af_aoede", "f"),
    ("KOKORO US Santa", "am_santa", "m"),
    ("KOKORO US Sky", "af_sky", "f"),
    ("KOKORO US Puck", "am_puck", "m"),
    ("KOKORO US Nova", "af_nova", "f"),
    ("KOKORO US Liam", "am_liam", "m"),
    ("KOKORO US Sarah", "af_sarah", "f"),
    ("KOKORO US Kore", "af_kore", "f"),
    ("KOKORO US Echo", "am_echo", "m"),
    ("KOKORO US Michael", "am_michael", "m"),

    # UK English (b) Voices
    ("KOKORO GB Alice", "bf_alice", "f"),
    ("KOKORO GB George", "bm_george", "m"),
    ("KOKORO GB Fable", "bm_fable", "m"),
    ("KOKORO GB Lily", "bf_lily", "f"),
    ("KOKORO GB Emma", "bf_emma", "f"),
    ("KOKORO GB Isabella", "bf_isabella", "f"),
    ("KOKORO GB Lewis", "bm_lewis", "m"),
    ("KOKORO GB Daniel", "bm_daniel", "m"),

    # Japanese (j) Voices
    ("KOKORO JP Nezumi", "jf_nezumi", "f"),
    ("KOKORO JP Tebukuro", "jf_tebukuro", "f"),
    ("KOKORO JP Kumo", "jm_kumo", "m"),
    ("KOKORO JP Gongitsune", "jf_gongitsune", "f"),
    ("KOKORO JP Alpha", "jf_alpha", "f"),

    # Hindi (h) Voices
    ("KOKORO HI Beta", "hf_beta", "f"),
    ("KOKORO HI Omega", "hm_omega", "m"),
    ("KOKORO HI Psi", "hm_psi", "m"),
    ("KOKORO HI Alpha", "hf_alpha", "f"),

    # Portuguese (p) Voices
    ("KOKORO PT Dora", "pf_dora", "f"),
    ("KOKORO PT Alex", "pm_alex", "m"),
    ("KOKORO PT Santa", "pm_santa", "m"),

    # Chinese (z) Voices
    ("KOKORO ZH Xiaoxiao", "zf_xiaoxiao", "f"),
    ("KOKORO ZH Yunxi", "zm_yunxi", "m"),
    ("KOKORO ZH Yunjian", "zm_yunjian", "m"),
    ("KOKORO ZH Xiaobei", "zf_xiaobei", "f"),
    ("KOKORO ZH Yunxia", "zm_yunxia", "m"),
    ("KOKORO ZH Yunyang", "zm_yunyang", "m"),
    ("KOKORO ZH Xiaoni", "zf_xiaoni", "f"),
    ("KOKORO ZH Xiaoyi", "zf_xiaoyi", "f"),

    # Italian (i) Voices
    ("KOKORO IT Nicola", "im_nicola", "m"),
    ("KOKORO IT Sara", "if_sara", "f"),

    # French (f) Voices
    ("KOKORO FR Siwis", "ff_siwis", "f"),

    # Spanish (e) Voices
    ("KOKORO ES Dora", "ef_dora", "f"),
    ("KOKORO ES Alex", "em_alex", "m"),
    ("KOKORO ES Santa", "em_santa", "m")
]
KOKORO_LANGUAGE_CODES = {
    'English (US)': 'a',
    'English (UK)': 'b',
    'Japanese': 'j',
    'Mandarin Chinese': 'z',
    'Spanish': 'e',
    'French': 'f',
    'Hindi': 'h',
    'Italian': 'i',
    'Portuguese (Brazil)': 'p'
}

INDIC_VOICES = {
    "Assamese": [("Amit", "Male"), ("Site", "Female")],
    "Bengali": [("Arjun", "Male"), ("Aditi", "Female")],
    "Bodo": [("Bikram", "Male"), ("Maya", "Female")],
    "Chhattisgarhi": [("Bhanu", "Male"), ("Champa", "Female")],
    "Dogri": [("Karan", "Male")],
    #"English": [("Thoma", "Mary")], # Uncomment that line if you want to support English language with this model
    "Gujarati": [("Yash", "Male"), ("Neha", "Female")],
    "Hindi": [("Rohit", "Male"), ("Divya", "Female")],
    "Kannada": [("Suresh", "Male"), ("Anu", "Female")],
    "Malayalam": [("Harish", "Male"), ("Anjali", "Female")],
    "Manipuri": [("Laishram", "Male"), ("Ranjit", "Male")],
    "Marathi": [("Sanjay", "Male"), ("Sunita", "Female")],
    "Nepali": [("Amrita", "Female")],
    "Odia": [("Manas", "Male"), ("Debjani", "Female")],
    "Punjabi": [("Divjot", "Male"), ("Gurpeet", "Female")],
    "Sanskrit": [("Aryan", "Male")],
    "Tamil": [("Jaya", "Female")],
    "Telugu": [("Prakash", "Male"), ("Lalitha", "Female")]
}
INDIC_LANG_CODES = {
    "Assamese": "as",
    "Bengali": "bn",
    "Bodo": "brx",
    "Chhattisgarhi": "hne",
    "Dogri": "doi",
    #"English": "en", # Also uncomment this line in order to support English language
    "Gujarati": "gu",
    "Hindi": "hi",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Manipuri": "mni",
    "Marathi": "mr",
    "Nepali": "ne",
    "Odia": "or",
    "Punjabi": "pa",
    "Sanskrit": "sa",
    "Tamil": "ta",
    "Telugu": "te"
}
