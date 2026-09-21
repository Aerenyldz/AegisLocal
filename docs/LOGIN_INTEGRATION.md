# Login entegrasyonu — MVP

## Temel karar

AegisLocal login formunun yerine geçmez ve kullanıcıya varsayılan olarak
"bir şeyi sürükle" demez. Şirket login sayfasına görünmez SDK eklenir; SDK
formun normal kullanımından davranışsal sinyaller toplar. Karar, login
endpoint'inin önündeki AegisLocal Gateway tarafından verilir.

```text
Login sayfası
  ├─ username/password formu
  ├─ Aegis SDK (görünmez, içerik okumaz)
  └─ yalnızca gerektiğinde challenge container
          |
          v
Login backend -> AegisLocal Gateway -> risk + policy -> allow/challenge/throttle/deny
```

## Şirket uygulamasına ne eklenir?

Entegrasyon için iki parça gerekir:

1. **Frontend SDK:** Sayfaya npm paketi veya tek bir yerel JavaScript bundle
   olarak eklenir. Login formunun bulunduğu root/container belirtilir.
2. **Backend middleware:** Login isteğiyle birlikte SDK'nın ürettiği kısa ömürlü
   risk/session token'ı AegisLocal'a iletir. Login servisi token kararını
   doğrulamadan kullanıcı oturumu açmaz.

Şirketin elle koordinat, buton uzaklığı veya canvas konumu ayarlaması
gerekmez. SDK DOM olaylarından form alanlarına odaklanma, alanlar arası
geçiş, pointer hareketinin doğal/otomatik oluşu, submit davranışı ve tarayıcı
sinyallerini çıkarır.

Şifre veya kullanıcı adı değeri **asla** AegisLocal'a gönderilmez. Klavye
toplama varsa yalnızca zaman aralıkları ve tuş sayısı gibi türetilmiş sinyal
kullanılır; karakter, field value ve gerçek içerik toplanmaz.

## Login akışı

### 1. Sayfa açılışı

Uygulama SDK'yı başlatır ve bir session oluşturur. SDK:

- pointer hareketlerini ve tıklama bağlamını,
- form alanlarına focus/blur zamanlarını,
- submit etkileşimini,
- webdriver/fingerprint sinyallerini

geçici bellekte toplar. Ham noktalar varsayılan olarak kalıcılaştırılmaz.

### 2. Submit öncesi

SDK mevcut davranıştan feature çıkarır ve Gateway'den karar token'ı ister.
Bu çağrı login şifresinden bağımsızdır.

### 3. Karar

| Risk | Kullanıcı deneyimi | Backend aksiyonu |
|---|---|---|
| düşük | Form normal gönderilir | `allow` |
| gri | Form duraklatılır, erişilebilir challenge açılır | `challenge` |
| yüksek | Kullanıcıya gereksiz challenge gösterilmez | `throttle` veya `deny` |

MVP'de `login_protection` profili gri bölgede challenge, yüksek riskte
throttle kullanır. Şirket isterse `high_assurance` ile yüksek riski deny
edebilir.

### 4. Challenge

Challenge konumu ve tasarımı host uygulamaya aittir. Önerilen arayüz:

- sayfanın altına sabit mesafeli bir widget değil,
- formun yanında veya erişilebilir modal içinde host'un verdiği
  `#aegis-challenge` container'ı,
- klavye ile erişilebilir, ekran okuyucu etiketleri olan doğrulama,
- başarılı olunca tek kullanımlık, kısa ömürlü token.

Challenge'ın kendi içindeki pointer hareketi yalnızca gri bölgeyi ayırt etmek
için kullanılır; ana ürün mantığı challenge'a dayanmaz.

### 5. Backend doğrulaması

Frontend'in "challenge geçti" demesi yeterli değildir. Login backend'i:

1. AegisLocal token'ını lokal Gateway'e doğrulatır,
2. token'ın session, endpoint ve policy ile eşleştiğini kontrol eder,
3. token geçerliyse login'i sürdürür,
4. token yoksa, süresi dolmuşsa veya tekrar kullanılmışsa isteği reddeder.

## Şirket entegrasyonu için önerilen sözleşme

Frontend:

```ts
const aegis = new AegisClient({
  baseUrl: "/aegis",
  policy: "login_protection",
  form: "#login-form",
  challengeContainer: "#aegis-challenge",
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const decision = await aegis.preflight("login");

  if (decision.enforcement === "challenge") {
    await aegis.completeChallenge();
  }

  loginForm.submit();
});
```

Backend'de policy adı frontend'den güvenilmemelidir. Gerçek üretim
entegrasyonunda `/login` route'u veya tenant konfigürasyonu server tarafında
`login_protection` profiline bağlanır. Frontend'deki policy yalnızca SDK
davranışını seçer; yetkili enforcement server tarafındadır.

## MVP'de yapılacak ve yapılmayacaklar

### Yapılacak

- SDK'ya form bağlama ve `preflight` sözleşmesi eklemek.
- Kararı ve challenge token'ını server tarafında doğrulamak.
- Host uygulamaya challenge container'ı sağlamak.
- Şifre içeriğinin ve form değerlerinin hiçbir aşamada toplanmadığını test
  etmek.
- Shadow mode'u login akışını bozmadan ölçüm için desteklemek.

### Yapılmayacak

- Şirketten piksel koordinatlarını elle ayarlamasını istemek.
- Şifreyi, kullanıcı adını veya tuş karakterlerini kaydetmek.
- Her login'de challenge göstermek.
- Sadece client'ın gönderdiği `allow` kararına güvenmek.
- Modelin kendi kendine üretimde eşik değiştirmesine izin vermek.
