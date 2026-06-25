# ⚡ STM32 Veri Kaydedici

STM32 mikrodenetleyiciden seri port (UART/USB) üzerinden veri okuyup `.txt` dosyasına kaydeden, grafik çizebilen masaüstü uygulaması.

---

## ⬇️ İndirme

Yukarıdaki **Actions** sekmesine git → En son tamamlanan build'e tıkla → **Artifacts** bölümünden indir.

| Platform | İndirilecek Dosya | Nasıl Çalıştırılır |
|---|---|---|
| 🍎 macOS | `STM32_Veri_Kaydedici_macOS.dmg` | İndir → Aç → Uygulamayı sürükle |
| 🖥️ Windows | `STM32_Veri_Kaydedici_Windows.exe` | İndir → Çift tıkla |

> **Not:** macOS'ta ilk açılışta "Bilinmeyen geliştirici" uyarısı çıkarsa:  
> **Sistem Tercihleri → Gizlilik ve Güvenlik → Yine de Aç** de.

---

## 🚀 Kullanım

1. STM32'yi USB ile bilgisayara bağla
2. Uygulamayı aç
3. **⟳** butonuna basarak COM portunu listele
4. Doğru portu ve baud rate'i seç (STM32 kodundakiyle aynı olmalı)
5. **▶ Bağlan** butonuna bas
6. Veriler otomatik olarak ekranda görünür ve dosyaya kaydedilir ✅

---

## ✨ Özellikler

- 🔌 Otomatik COM port algılama (Windows: `COM3`, macOS: `/dev/tty.usbmodem...`)
- 💾 Zaman damgalı `.txt` dosyasına otomatik kayıt
- 📈 Kaydedilen verilerden grafik oluşturma (zoom, pan, PNG kaydet)
- 📡 Gelen verileri anlık gösteren renkli terminal
- 📊 Toplam satır, son veri ve bağlantı süresi istatistikleri
- 🖤 Koyu tema arayüz

---

## 📄 Kayıt Formatı

Her satır şu şekilde kaydedilir:

```
[2025-06-25 16:35:00] Sicaklik:25.3
[2025-06-25 16:38:00] Sicaklik:26.1
```

---

## 🛠️ STM32 Tarafı

STM32'nin her 3 dakikada bir şu şekilde veri göndermesi yeterli:

```c
// Örnek: HAL ile UART üzerinden veri gönder
char msg[] = "Sicaklik:25.3\r\n";
HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);
```

---

## 🛠️ Geliştirici — Kaynak Koddan Çalıştırma

```bash
pip install pyserial matplotlib
python main.py
```

