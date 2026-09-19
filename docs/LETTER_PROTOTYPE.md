# Harf challenge ilk prototipi

## Çalıştırma

En kolay yol, `scripts\start-prototype.bat` dosyasına çift tıklamaktır. Bu dosya
API'yi, challenge web sunucusunu ve tarayıcı sayfasını otomatik başlatır.

Elle çalıştırmak isterseniz:

1. API'yi başlatın:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --port 8001
```

2. `scripts\letter-challenge.html` dosyasını Chrome/Edge'de açın.
3. Gösterilen harfi canvas üzerinde doğal bir hareketle çizin.
4. `Çizimi analiz et` butonuna basın.

Ekran, PoW çözer ve mouse trajectory'sini `POST /v1/analyze/mouse`
endpoint'ine gönderir. Sonuçta karar, risk skoru, nedenler ve XAI katkıları
gösterilir.

## Bot smoke testi

API çalışırken:

```powershell
$env:AEGIS_API="http://127.0.0.1:8001"
python scripts\bot_letter_probe.py --letter A
```

Bu probe, düzenli ve `webdriver=true` işaretli trajectory gönderir. Gerçek bir
ML modeli değildir; ilk prototipte karar akışını ve insan/bot veri formatını
doğrulamak içindir.

## Veri toplama planı

- İnsan: 5-8 farklı harf, her harf için en az 20 doğal çizim.
- Bot: düz çizgi, sabit hız, Bezier ve Playwright varyantları; her harf için en az 20 örnek.
- JSONL satırları `label`, `points`, `webdriver`, `pow_ok` alanlarıyla saklanır.
- İnsan verisi ve ham bot kayıtları Git'e eklenmez.
