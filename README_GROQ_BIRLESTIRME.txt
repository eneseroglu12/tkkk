JUNIOR WINGS — FİLTRELİ + GROQ DESTEKLİ SÜRÜM

Çalıştırma (Windows PowerShell):
  py -m pip install -r requirements.txt
  py -m streamlit run app.py

Tarayıcı: http://localhost:8501

Birleştirilen özellikler:
- Kırmızı/siyah/krem sade THY tema, sadece THY logosu.
- Karar ve aşama filtreleri, başvuru ID veya anonim aday ID ile arama.
- 13 kayıt temelli e-posta kuralı; Türkçe ve İngilizce taslaklar.
- İK kanıt ekranı, bireysel onay ve aşama kesinleşme kontrolü, toplu CSV.
- Gelen yanıt sınıflandırma ve rapor.
- İsteğe bağlı Groq AI ile iki taslağa dil düzenleme önerisi. API anahtarı sol panelde;
  kullanıcı onayı olmadan dış API'ye metin gönderilmez. Anahtar kodda saklanmaz.
  Groq'dan dönen metin doğrudan onaylı taslağa geçmez; yalnızca öneri gösterilir.
- Türkçe/İngilizce temel sayısal, ID/kod ve ret türü kontrolü; anlamsal eşitliği garanti etmez.

ÖNEMLİ: Groq kullanılması halinde aday e-posta metni üçüncü taraf API hizmetine aktarılır;
kurumunuzun gizlilik/veri işleme politikalarına uygun kullanım gerekir. Excel'in tamamı
gönderilmez. Model adı veya erişim Groq hesabınıza göre değişebilir; modeli sol menüden ayarlayın.
İK onayları yalnızca oturumda saklanır; gerçek gönderim entegrasyonu yoktur.

Arkadaşın sürümündeki yeniden görüşme daveti otomatik eklenmedi: yeni kontenjan
ve yeniden görüşmeye çağrı kararı doğrulanmış kaynakla tutulmadığı sürece
adaylara yeni davet oluşturulmamalıdır.
