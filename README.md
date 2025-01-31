# NeviTechTTS

## Kullanım için gerekenler
1. .env dosyasına eklenmesi gerekenler
   AWS_ACCESS_KEY_ID=<here>
   AWS_SECRET_ACCESS_KEY=<here>

2. certificate_constants.py dosyasında KEY_PATH ve CERT_PATH düzenlenmeli

```bash
pip install -r requirements.txt
python POLLY_TTS/app.py
```



# TODO
- KOKORO dosyalarını POLLY_TTS içine de kopyaladım, import ederken hata alıyordum, düzenlenmesi gerek



Şuan 5 model kullanıyor
1. AWS Polly
2. XTTS v2
3. indic-parler-tts-pretrained
4. viXTTS
5. Kokoro-82M v0_19

   
