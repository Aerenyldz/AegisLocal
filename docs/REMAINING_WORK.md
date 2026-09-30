# AegisLocal — Kalan İşler ve Uygulama Planı

Bu belge, AegisLocal MVP'sinin mevcut durumunu ve MVP'den kontrollü pilot/v1.0
seviyesine geçmek için kalan işleri tanımlar.

## 1. Mevcut durum

Yerel MVP aşağıdaki parçalarla çalışır durumdadır:

- FastAPI tabanlı yerel bot-defense gateway
- Mouse davranışı için FFT özellik çıkarımı ve heuristik risk skoru
- `allow`, `challenge`, `throttle` ve `deny` enforcement kararları
- `default`, `login_protection` ve `high_assurance` policy profilleri
- Shadow mode
- XAI/reason kodları ve model sürümü
- PoW challenge/proof ve tek kullanımlık doğrulama
- Physics challenge ve challenge-token bağlama
- Audit kayıtları, özet/evaluation/export endpoint'leri
- Model status endpoint'i ve Prometheus metrikleri
- TypeScript client SDK temeli
- Demo, login prototipi ve operator dashboard ekranları
- Docker Compose altyapısı
- İnsan/bot simülasyon ve dataset değerlendirme araçları
- Windows başlatma script'leri

Son doğrulamalar:

| Kontrol | Sonuç |
|---|---:|
| Backend pytest | 22/22 geçti |
| Rust PoW testleri | 1/1 geçti |
| TypeScript SDK typecheck | Başarılı |
| Docker Compose config | Başarılı |
| Health load smoke, 100 istek/10 worker | %0 hata |
| Sentetik dataset pipeline | Çalışıyor |

Sentetik dataset sonucu pipeline bağlantısını doğrular; production kalitesi
ve gerçek kullanıcı davranışı için kanıt sayılmaz.

## 2. Öncelik sırası

İşler aşağıdaki sırayla yapılmalıdır:

1. Gerçek ve izinli dataset toplama
2. Gerçek metrikleri ve release raporunu üretme
3. Pilot öncesi güvenlik ve operasyon hazırlığı
4. Login endpoint'inde shadow pilot
5. Kontrollü enforcement
6. Üretim hardening ve v1.0 release candidate

Bu sıra değiştirilmemelidir. Gerçek veri ve shadow gözlemi yapılmadan
production `deny` enforcement açılmamalıdır.

## 3. Gerçek dataset toplama

### 3.1 İnsan oturumları

İnsan verisi açık rıza ile toplanmalıdır. Her kayıt için:

- Anonim oturum kimliği
- Etiketleme kaynağı ve etiket güveni
- Tarayıcı ailesi
- İşletim sistemi ailesi
- Pointer türü ve touch capability
- Gönüllü/izinli collection context
- Ham trajectory retention tercihi

Kayıtlarda aşağıdakiler tutulmamalıdır:

- IP adresi
- User-Agent'ın tamamı
- Kullanıcı adı, e-posta veya hesap kimliği
- Parola, form değeri veya ödeme verisi
- Ham trajectory'nin zorunlu olmayan kalıcı kopyası

İlk anlamlı benchmark için önerilen minimum:

- En az 200 insan oturumu
- En az 5 tarayıcı/işletim sistemi kombinasyonu
- Mouse, touch ve mümkünse trackpad çeşitliliği
- Oturumların en az bir kısmında düşük hareketli/klavye ağırlıklı akış

### 3.2 Bot corpus

Bot verisi en az şu aileleri içermelidir:

- Düz lineer hareket
- Bézier veya cubic hareket
- Playwright
- Puppeteer/Selenium
- `navigator.webdriver` açık ve kapalı varyantlar
- Düşük tremor ve sabit hız profili
- Replay edilmiş trajectory
- PoW eksik veya geçersiz istek

Her bot ailesi için aynı minimum kayıt sayısı ve ayrıştırılabilir
`bot_family` etiketi kullanılmalıdır. Bot datası insan datasından daha kolay
olduğu için release gate'in yalnızca sentetik botlarla geçilmesine izin
verilmemelidir.

### 3.3 Dataset kalite kontrolü

Her değerlendirme öncesi şu kontroller yapılmalıdır:

- JSONL parse edilebilir mi?
- Her kayıt `human` veya `bot` etiketi taşıyor mu?
- Mouse kaydında en az 8 nokta var mı?
- Duplicate `event_id` var mı?
- Her iki sınıfta yeterli örnek var mı?
- Bot ailesi dağılımı dengeli mi?
- Metadata coverage ölçülebilir mi?
- Ham veri retention politikası uygulanıyor mu?

Örnek komutlar:

```powershell
python scripts\tools\dataset_manifest.py `
  datasets\raw\pilot-v0.1.jsonl `
  --output datasets\processed\pilot-v0.1.manifest.json

python scripts\tools\evaluate_dataset.py `
  datasets\raw\pilot-v0.1.jsonl `
  > datasets\processed\pilot-v0.1.evaluation.json
```

## 4. Gerçek release ölçümleri

Release değerlendirmesi en az aşağıdaki değerleri raporlamalıdır:

- ROC-AUC: en az `0.85`
- Bot TPR: en az `%85`
- İnsan FPR: en fazla `%2`
- Her sınıfta yeterli örnek
- Duplicate event ID: `0`
- Gerçek yük testinde hata oranı: en fazla `%1`
- Analyze endpoint p50/p95 latency
- PoW çözüm süresi
- Challenge completion rate
- Policy ve model sürümü

Release gate:

```powershell
python scripts\tools\release_check.py `
  datasets\processed\pilot-v0.1.evaluation.json `
  --load-report artifacts\load-report.json
```

Gate başarısızsa enforcement açılmamalı; önce veri kalitesi, eşikler veya
model davranışı incelenmelidir.

## 5. Pilot öncesi güvenlik ve operasyon hazırlığı

### 5.1 Secret yönetimi

Production secret'ları `.env` veya Git'e yazılmamalıdır. Aşağıdaki değerler
secret store, deployment secret veya işletim sistemi secret mekanizmasından
sağlanmalıdır:

- Service API key
- Challenge signing secret
- Redis authentication
- Database credentials
- TLS private key

### 5.2 Ağ ve kimlik doğrulama

- API yalnızca güvenilir reverse proxy arkasında yayınlanmalı.
- TLS zorunlu olmalı.
- Operator dashboard kimlik doğrulaması olmadan açılmamalı.
- Proxy header'ları yalnızca güvenilen proxy IP'lerinden kabul edilmeli.
- CORS production origin listesiyle sınırlandırılmalı.
- Health endpoint'i ile authenticated endpoint ayrımı belgelenmeli.

### 5.3 Persistence ve retention

- Redis için TTL ve single-use challenge davranışı doğrulanmalı.
- Audit persistence yedekleme ve retention süresi belirlenmeli.
- Ham trajectory kalıcı saklama varsayılan olarak kapalı kalmalı.
- Audit export erişimi yetkilendirilmeli ve loglanmalı.
- Model/policy manifestleri sürümlenmeli.

### 5.4 Rollback

Rollback, pilot başlamadan önce denemelidir:

1. Policy mode'unu `shadow` yap.
2. Son çalışan model ve policy manifestine dön.
3. Önceki container/image sürümünü sabitle.
4. Secret ve environment sürümlerini geri al.
5. Son 24 saatlik audit export'unu al.
6. Olay, neden ve geri dönüş zamanını kaydet.

## 6. Shadow pilot

İlk pilot yalnızca bir endpoint'te, tercihen login akışında yapılmalıdır.

### Başlangıç

- Policy: `login_protection`
- Mode: `shadow`
- Süre: en az 24 saat
- Kullanıcı erişimi: enforcement tarafından değiştirilmemeli
- Kararlar ve nedenler audit'e yazılmalı

### İzlenecek metrikler

- Allow/challenge/throttle/deny dağılımı
- İnsan false-positive oranı
- Login başarı oranı
- Analyze p50/p95 latency
- Challenge başlatma ve tamamlama oranı
- PoW başarısızlık oranı
- Endpoint ve policy bazında karar dağılımı
- Model/policy sürümüne göre drift

### Shadow çıkış kriterleri

- Kritik hata veya veri sızıntısı yok
- Ham trajectory beklenmedik şekilde kalıcı tutulmuyor
- İnsan FPR kabul sınırının altında
- Login başarı oranında anlamlı düşüş yok
- Audit ve rollback akışı doğrulanmış
- Operatörler karar nedenlerini açıklayabiliyor

## 7. Kontrollü enforcement

Shadow kriterleri sağlandıktan sonra enforcement kademeli açılmalıdır:

1. Önce yalnızca açık bot sinyallerinde `throttle`.
2. `deny` başlangıçta kapalı veya manuel incelemeye bağlı.
3. Küçük trafik yüzdesiyle canary.
4. Kullanıcı şikayetleri ve login başarı oranını izle.
5. İnsan FPR `%2` üzerine çıkarsa derhal shadow mode'a dön.
6. Her eşik/policy değişikliğini sürüm ve tarih ile kaydet.

Ödeme, yönetici ve kupon akışları login pilotu stabil olmadan açılmamalıdır.
Her kritik endpoint'in ayrı eşiği ve rollback planı bulunmalıdır.

## 8. Teknik geliştirme sırası

### Faz A — PoW ve challenge üretim kalitesi

- Rust/WASM build pipeline'ını CI'a ekle.
- WASM ve JS fallback için parity testi yaz.
- Difficulty 12–22 aralığını gerçek cihazlarda ölç.
- Nonce TTL, replay ve clock skew testlerini Redis ile çalıştır.
- WCAG 2.2 AA alternatif challenge akışını tamamla.

### Faz B — Model ve açıklanabilirlik

- İnsan çeşitliliğiyle baseline'ı yeniden kalibre et.
- Isolation Forest/ONNX modelini offline train ve export et.
- Artifact hash ve model manifest zorunlu yap.
- Feature contribution ve reason sözleşmesini sabitle.
- Shadow mode'da drift alarmı ekle.

### Faz C — Physics Canvas ve SDK

- Challenge issue/verify akışını SDK'ya bağla.
- Seed ve physics parametrelerinin server-side doğrulamasını tamamla.
- Trajectory hash ve timing bounds replay'e dayanıklı olmalı.
- Erişilebilir alternatif challenge sun.
- Gray zone akışını uçtan uca test et:
  `gray -> challenge -> allow/deny`.

### Faz D — Production hardening

- Docker image ve environment secret hardening
- Reverse proxy/TLS örneği
- Redis/Postgres persistence ve backup
- Authenticated dashboard
- 1k RPS kontrollü load testi
- Threat model ve security checklist
- Tek makineden tekrar kurulabilir release candidate

## 9. v1.0 kabul kriterleri

v1.0 release candidate ancak aşağıdakiler tamamlandığında hazırlanmalıdır:

- Gerçek ve izinli dataset ile release gate geçti.
- İnsan FPR ve bot TPR hedefleri pilotta korundu.
- En az bir login shadow pilotu tamamlandı.
- Rollback tatbikatı başarıyla yapıldı.
- TLS ve dashboard authentication aktif.
- Secret'lar kaynak kod dışında tutuluyor.
- Audit retention ve export politikası yazılı.
- Redis challenge/replay davranışı dağıtık senaryoda test edildi.
- PoW fallback ve erişilebilirlik akışı doğrulandı.
- 1k RPS veya hedeflenen gerçek trafik yük testi raporlandı.
- Kurulum başka bir makinede tekrarlandı.
- Model, policy, image ve dataset manifestleri sürümlü.

## 10. İlk yapılacak işler

Kısa vadede uygulanacak sıra:

1. Consent metni ve collection context sözleşmesini kesinleştir.
2. Gerçek insan collector'ını kontrollü pilot ortamında aç.
3. Bot corpus üretimini aynı schema ile çalıştır.
4. Dataset manifest ve evaluation raporlarını üret.
5. Gerçek load report oluştur.
6. Release gate'i çalıştır.
7. Gate geçerse login shadow pilotunu başlat.

Bu adımlar tamamlanmadan sistemin kullanıcı erişimini değiştiren production
enforcement moduna alınmaması gerekir.
