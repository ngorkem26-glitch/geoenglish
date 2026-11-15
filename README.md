# GeoEnglish

Kişisel İngilizce öğrenme sitesi: HTML/CSS/JavaScript + JSON + günlük Python/OpenAI otomasyonu.

## Yerelde çalıştırma

```bash
python -m http.server 8000
```

Ardından http://localhost:8000 adresini açın. `index.html` dosyasını `file://` olarak açmayın; tarayıcı JSON erişimini engelleyebilir.

## İçerik üretimi

Python 3.12+ ile:

```bash
python -m pip install -r requirements.txt
python scripts/generate_lesson.py --dry-run
```

Gerçek içerik üretimi için OpenAI API anahtarını **ortam değişkeni** `OPENAI_API_KEY` olarak ayarlayın (ChatGPT aboneliğinden ayrı ücretlendirilir):

```bash
python scripts/generate_lesson.py
```

Komut, `data/curriculum.json` dosyasındaki henüz yayımlanmamış ilk konuyu seçer. İsteğe bağlı manuel kullanım:

```bash
python scripts/generate_lesson.py --topic 'Climate and weather' --level A1
```

Aynı konu ve seviye ikinci kez yayımlanmaz. Müfredattaki konular bitince yeni içerik üretimi durur; yeni konular eklenmelidir.

## GitHub Pages ve günlük otomasyon

1. Dosyaları **public** GitHub deposuna yükleyin.
2. Repo **Settings → Pages → Build and deployment → Deploy from a branch**, `main` / `(root)` seçin.
3. Repo **Settings → Secrets and variables → Actions → New repository secret** altında `OPENAI_API_KEY` ekleyin.
4. **Settings → Actions → General → Workflow permissions** bölümünde yazma izninin verildiğini kontrol edin.
5. **Actions → GeoEnglish - Daily 09:00 TRT → Run workflow** ile önce manuel test edin.
6. Zamanlayıcı `0 6 * * *` ile her gün **09.00 Türkiye saati** için planlanmıştır; GitHub Actions gecikebilir veya atlanabilir.

**Not:** Gerçek API çağrısı, GitHub yüklemesi ve otomatik yayınlama bu arşivi oluştururken gerçekleştirilmedi. Üretilen içerikler yapısal olarak denetlenir ancak dilsel/bilimsel doğruluk için insan kontrolü önerilir. API anahtarını asla web arayüzüne koymayın. Tarayıcı ilerlemesi cihazın yerel depolamasında saklanır; cihazlar arası senkronize edilmez.

## Dosyalar

- `index.html` ana sayfa
- `lesson.html` ders sayfası
- `css/style.css` responsive tasarım
- `js/app.js` ders listesi, arama, test ve ilerleme
- `data/lessons-index.json` içerik deposu
- `data/curriculum.json` üretilecek sıradaki konular
- `scripts/generate_lesson.py` GPT-4o-mini içerik üretimi
- `.github/workflows/daily-lesson.yml` günlük otomasyon
- `tests/test_content.py` veri tutarlılığı testleri

## Professional arayüz güncellemesi

- Ana sayfa: coğrafya temalı özgün CSS dünya görseli, responsive üst menü, öğrenme yol haritası, ilerleme özeti ve ders kütüphanesi.
- Ders sayfası: okunabilir ders içeriği, kelime kartları, sesli cümle örnekleri, mini sınav ve tamamlanma işaretleme.
- Ders sıralaması `created_at` alanına göre yeniden eskiye yapılır. Tamamlama bilgileri yalnızca kullanılan tarayıcının `localStorage` alanında tutulur; hesaplar arası senkronizasyon yoktur.
- Görsel tasarım harici görsel dosyası gerektirmez. Google Fonts yüklenemezse sistem fontları kullanılır.
- Günlük üretim iş akışı için GitHub Actions ve OpenAI API anahtarı ayrıca yapılandırılmalıdır. API çağrısı bu paket hazırlanırken yapılmamıştır.
- GitHub Pages proje deposunda site kökünden yayınlanmalıdır (`main`, `/(root)`).
- Otomatik üretilen bilimsel içerikler yayınlanmadan önce editoryal denetim gerektirebilir.
