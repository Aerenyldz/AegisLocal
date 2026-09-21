# AegisLocal MVP — Ürün ve Uygulama Planı

## 1. MVP'nin tek cümlelik amacı

AegisLocal, kurumun kendi altyapısında çalışan ve hassas web akışlarında
telemetriyi dışarı çıkarmadan **allow / observe / challenge / throttle /
deny** kararı veren açıklanabilir bir Bot Defense Gateway'dir.

MVP'nin amacı yeni bir CAPTCHA türü yapmak değil, bu karar döngüsünü
kurulabilir ve ölçülebilir bir ürün olarak kanıtlamaktır.

## 2. Hedef müşteri ve ilk kullanım alanı

İlk sürüm genel amaçlı bütün web sitelerini hedeflemez. Öncelik:

- login, kayıt, şifre sıfırlama ve kupon/ödeme endpoint'leri,
- KVKK/GDPR veya air-gapped çalışma zorunluluğu olan kurumlar,
- üçüncü taraf CAPTCHA ve telemetri sağlayıcısı kullanmak istemeyen ekipler.

İlk başarı kriteri:

> Gerçek kullanıcıların çoğu görünmez biçimde geçerken, otomasyon trafiği
> açıklanabilir sinyallerle ayrıştırılmalı ve operatör karar politikasını
> değiştirebilmelidir.

## 3. MVP kapsamı

### Dahil

1. TypeScript SDK ile tarayıcı sinyallerinin toplanması.
2. Ham verinin varsayılan olarak kalıcı saklanmaması.
3. Yerel FFT/heuristic risk motoru; daha sonra ONNX motoruyla değiştirilebilir.
4. Policy profili: endpoint'e göre eşik ve aksiyon.
5. Açıklanabilir karar çıktısı: skor, nedenler, özellikler, model/policy sürümü.
6. Rate limit ve tek kullanımlık PoW.
7. Shadow mode: karar üret, fakat erişimi değiştirme.
8. Operatör etiketlemesi ve model sürümleme için veri sözleşmesi.
9. Docker ile API + Redis kurulumu ve health/metrics endpoint'leri.

### MVP dışında

- Küresel tehdit istihbaratı veya zorunlu dış API,
- otomatik ve denetimsiz online retraining,
- ilk sürümde GRU/LSTM,
- physics canvas'ı ana doğrulama mekanizması yapmak,
- çoklu dilde SDK'ları ilk günden tamamlamak.

Physics challenge yalnızca gri bölgede kullanılan, erişilebilir bir fallback
olarak kalır.

## 4. Hedef mimari

```text
Browser / Server SDK
        |
        v
Local Gateway API
  ├─ Request context (tenant, endpoint, session)
  ├─ Rate limit + replay/PoW guard
  ├─ Feature extraction (ham veri geçici)
  ├─ Risk engine (heuristic -> ONNX)
  ├─ Policy engine
  └─ Decision + XAI + audit event
        |
        +--> Redis: nonce, rate limit, kısa ömürlü session state
        +--> Local audit store: türetilmiş özellikler, karar, etiket
        +--> Metrics: latency, karar dağılımı, false-positive sinyalleri
```

Katman kuralları:

- **SDK** yalnızca sinyal toplar ve normalize eder; karar vermez.
- **Risk engine** yalnızca skor ve kanıt üretir; allow/deny politikası uygulamaz.
- **Policy engine** endpoint politikasını skora ve kanıta bağlar.
- **Audit** ham trajectory değil, türetilmiş veri ve karar kanıtlarını saklar.
- **Training** aktif üretim modelini kendiliğinden değiştiremez.

## 5. Karar sözleşmesi

Her analiz cevabı aşağıdaki anlamı taşımalıdır:

```json
{
  "decision": "observe",
  "risk_score": 0.61,
  "label": "gray",
  "reasons": ["path_too_smooth", "velocity_too_regular"],
  "xai": {
    "path_too_smooth": 0.22,
    "velocity_too_regular": 0.18
  },
  "policy": "login_protection",
  "enforcement": "allow",
  "model_version": "heuristic-0.1.0"
}
```

`decision` gözlemlenen risk sınıfıdır; `enforcement` ise politikanın
uyguladığı aksiyondur. Böylece shadow mode'da risk yüksek olsa bile kullanıcı
engellenmez.

## 6. Policy profilleri

Başlangıçta üç profil yeterlidir:

| Profil | Amaç | Önerilen davranış |
|---|---|---|
| `default` | Genel sayfalar | düşük riskte allow, gri bölgede observe |
| `login_protection` | Login/kayıt/şifre | gri bölgede challenge, yüksek riskte throttle |
| `high_assurance` | Ödeme/admin/kupon | gri bölgede challenge, yüksek riskte deny |

Her profil `shadow_mode`, `allow_threshold`, `challenge_threshold` ve
`deny_action` değerlerini taşır. Eşikler ortam değişkenleriyle değil,
versiyonlanabilir yerel policy dosyasıyla yönetilmeye başlanmalıdır.

## 7. Güvenli öğrenme döngüsü

```text
observe -> operatör etiketi -> dataset snapshot
        -> offline evaluation -> shadow deploy
        -> false-positive kapısı -> aktif model
```

Aktif model için minimum kapılar:

- insan false-positive oranı ölçülmeden yayın yok,
- model ve dataset hash'i kaydedilmeden yayın yok,
- önceki modelden anlamlı kötüleşme varsa otomatik rollback,
- ham veri retention açıkça etkinleştirilmedikçe kapalı.

## 8. Uygulama sırası ve Definition of Done

Login formu için kullanıcı akışı ve entegrasyon sözleşmesi:
[LOGIN_INTEGRATION.md](LOGIN_INTEGRATION.md).

### Sprint 1 — Ürün omurgası

- [ ] Policy modelleri ve varsayılan profiller.
- [ ] Analyze isteğinde `policy` ve `mode` bağlamı.
- [ ] Response'ta `policy`, `enforcement`, `model_version`.
- [ ] Mevcut heuristic scorer policy engine arkasına alınır.
- [ ] S1–S5 senaryoları policy bazında test edilir.

### Sprint 2 — Operasyonel gözlem

- [x] Audit event şeması.
- [x] Son kararları lokal olarak sınırlı bellekte görüntüleme endpoint'i.
- [ ] Karar dağılımı, latency ve challenge oranı metrikleri.
- [ ] Basit lokal JSONL/Postgres adapter sınırı.
- [ ] Shadow mode varsayılanı ve üretim güvenlik notları.

### Sprint 3 — Entegrasyon

- [ ] Nginx/Envoy örnek entegrasyonu.
- [ ] Login örnek uygulaması.
- [ ] Docker Compose ile tek komut kurulum.
- [ ] SDK için yayınlanabilir paket ve entegrasyon dokümanı.

### Sprint 4 — Öğrenme ve kanıt

- [x] İnsan/bot/uncertain operatör etiketleme endpoint'i.
- [x] Etiketli karar kanıtlarını JSONL export etmek.
- [x] Offline değerlendirme: TPR, FPR, ROC-AUC ve veri yeterliliği.
- [ ] ONNX scorer shadow deployment.
- [ ] Model registry ve rollback sözleşmesi.

## 9. MVP'nin ölçüleceği metrikler

- İnsan false-positive oranı: hedef `< %2`.
- Bot yakalama oranı: hedef dataset üzerinde `>= %85`.
- Analyze p95 latency: yerel CPU'da `< 50 ms` (PoW hariç).
- Dış ağ bağımlılığı: varsayılan kurulumda `0`.
- Ham trajectory kalıcı retention: varsayılan `0`.
- Kararların XAI reason içermesi: `%100`.

Bu eşikler laboratuvar başlangıç hedefidir; gerçek müşteriye sunulmadan önce
kurumun kendi baseline'ı ile yeniden kalibre edilir.
