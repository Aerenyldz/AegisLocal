# AegisLocal pilot and v1.0 runbook

Bu runbook, sistemi gerçek bir login veya kritik endpoint'e kontrollü biçimde
bağlamak içindir. Pilot **önce shadow mode** ile başlar; ölçümler kabul
edilmeden kullanıcı erişimi değişmez.

## Pilot öncesi çıkış kapısı

Release kontrolü aşağıdaki değerleri arar:

- Dataset karşılaştırmaya hazır,
- ROC-AUC `>= 0.85`,
- Bot TPR `>= 0.85`,
- İnsan false-positive oranı `<= %2`,
- Yük testi hata oranı `<= %1`,
- API key ve challenge secret üretim secret store'dan geliyor,
- TLS reverse proxy ve dashboard kimlik doğrulaması hazır,
- Rollback adımı denenmiş.

Otomatik kontrol:

```powershell
python scripts\tools\release_check.py `
  datasets\processed\phase3-labeled-v0.1-clean.evaluation.json `
  --load-report artifacts\load-report.json
```

`release_check.py` başarısızsa pilot enforcement başlatılmaz.

## Aşama 1 — Shadow pilot

1. Tek bir endpoint seç: tercihen login.
2. Policy'yi server tarafında `login_protection` olarak sabitle.
3. Analyze isteğinde `mode=shadow` kullan.
4. En az 24 saat kararları izle.
5. Dashboard'da allow/challenge/throttle/deny dağılımını, p95 latency'yi
   ve etiketlenen insan false-positive oranını kontrol et.
6. Karar kanıtlarında parola, form değeri veya ham trajectory olmadığını kontrol et.

Shadow pilotta hiçbir karar kullanıcıyı engellememelidir.

## Aşama 2 — Kontrollü enforcement

1. Yalnızca açık bot sinyallerinde `throttle` etkinleştir.
2. `deny` kararını başlangıçta kapalı tut veya manuel incelemeye bağla.
3. Gerçek kullanıcı şikayetlerini ve login başarı oranını izle.
4. Her policy değişikliğini versiyon ve tarih ile kaydet.
5. İnsan false-positive oranı `%2` üzerine çıkarsa hemen shadow mode'a dön.

## Aşama 3 — Kritik akışlar

Ödeme, yönetici ve kupon akışları ancak login pilotu stabil olduktan sonra
`high_assurance` policy ile ayrı ayrı açılır. Her endpoint için ayrı eşik,
rollback ve kabul kriteri bulunur.

## Rollback

- Uygulama policy'sini `mode=shadow` yap.
- Son çalışan model/policy manifestine dön.
- Docker image ve environment secret sürümünü sabitle.
- Son 24 saatin audit export'unu al.
- Olayı, nedeni ve geri dönüş zamanını operatör kaydına yaz.

## v1.0 kabulü

v1.0 yalnızca pilot süresince ölçümler stabil kaldığında, rollback denendiğinde
ve kurulum başka bir makinede tekrar edilebildiğinde yayınlanır. Laboratuvar
dataset'i tek başına gerçek müşteri trafiği kabulü değildir.
