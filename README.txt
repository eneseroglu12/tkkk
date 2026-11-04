JUNIOR WINGS — 13 KURALLI E-POSTA TASLAĞI VE İK ONAY MVP
=========================================================

WINDOWS'TA ÇALIŞTIRMA
1. ZIP dosyasını bir klasöre çıkarın.
2. Klasörün adres çubuğuna powershell yazıp Enter'a basın.
3. py -m pip install -r requirements.txt
4. py -m streamlit run app.py
5. Tarayıcı: http://localhost:8501

PROJE DOSYALARI
- app.py: Streamlit arayüzü, bireysel İK onayı, toplu hazırlık, gelen yanıtlar, raporlar.
- email_rules.py: kaynak ve karar denetimleri, şablon/alt kategori seçimi, başarı doğrulama,
  kanıta dayalı olumsuz e-posta oluşturma ve gelen yanıt sınıflandırması.
- 02_Veriler.xlsx: özgün örnek veri, değiştirilmeden korunmuştur.
- requirements.txt: bağımlılıklar.

TEMEL KURALLAR
- OLUMSUZ önceliklidir; KABUL ve DEVAM_EDIYOR ayrı iletişim akışına ayrılır,
  bu iki grup için otomatik ret/kabul e-postası üretilmez.
- Geçme barajları ve kurum içi notlar aday e-postasına yazılmaz.
- Önceki başarılar yalnız sınavların GECTI sonuçları veya açık İK geçiş kararı ile kanıtlanır.
- Kontenjan kararına beceri eksikliği veya gelişim tavsiyesi eklenmez.
- Eksik, çelişkili, düzeltilmiş veya paylaşımı yasak kaynaklar İK incelemesine gider.
- İK onayı, kaynak verinin ve taslağın parmak izine bağlanır; değişiklik onayı geçersiz kılar.
- Aşama kesinleşmesi ayrıca doğrulanır; yalnız onaylı kayıtlar CSV olarak hazırlanır.
- Gelen aday yanıtları manuel girilir, sınıflandırılır ve İK tarafından düzenlenip onaylanır.

ÖNEMLİ SINIRLAR
- Gerçek e-posta gönderimi, e-posta gelen kutusu bağlantısı, rol bazlı kimlik doğrulama
  ve kalıcı sunucu veri tabanı yoktur. Bunlar üretim sistemi için ayrıca gerekir.
- İK onayları yalnız Streamlit oturumunda saklanır; uygulama yeniden başlatılırsa silinir.
- Düzenlenen taslaklarda temel güvenlik kontrolü olsa da anlamsal ve kurumsal nihai
  kontrol İK sorumluluğundadır.
- Şablon üretimi deterministiktir; harici AI API anahtarı gerektirmez.
- Türkçe aday e-postalarında gerçek kişisel veri bulunmadığı için 'Sayın Adayımız' hitabı kullanılır.


İK e-posta taslakları hem Türkçe hem İngilizce üretilir. Her iki dil bağımsız biçimde düzenlenebilir ve birlikte İK onayına tabidir. Herhangi birinin değiştirilmesi önceki onayı geçersiz kılar. Toplu CSV iki dili de içerir.


Ek not: Bu sürüm THY renklerinde (kırmızı-beyaz-krem) kullanıcı dostu arayüz ve yerleşik logo/görseller ile gelir.

Bu sürümde yalnızca THY logosu kullanılır; tema kırmızı-siyah-krem paletine göre düzenlenmiştir.
