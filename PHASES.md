# Development Phases

Bu doküman, [PRD.md](PRD.md) dosyasında tanımlanan proje kapsamına göre geliştirme fazlarını açıklar.

Amaç, PostgreSQL ve MongoDB performansını karşılaştıran web tabanlı benchmarking platformunu kontrollü ve sıralı şekilde geliştirmektir. Fazlar backend, frontend, Docker ortamı, benchmark engine, metrik hesaplama ve sonuç gösterimi işlerini birlikte ele alır.

---

## Phase 1: Project Setup

### Goal

Frontend, backend, PostgreSQL ve MongoDB servislerinden oluşan temel proje yapısını hazırlamak.

### Tasks

- [x] Frontend projesini oluştur.
- [x] Backend projesini oluştur.
- [x] Docker Compose dosyasını oluştur.
- [x] PostgreSQL container servisini ekle.
- [x] MongoDB container servisini ekle.
- [x] Backend için temel API yapısını hazırla.
- [x] Frontend için temel dashboard sayfasını hazırla.
- [x] Backend ile frontend arasında temel bağlantıyı kur.
- [x] Backend ile PostgreSQL bağlantısını test et.
- [x] Backend ile MongoDB bağlantısını test et.

### Deliverables

- [x] Çalışan frontend uygulaması
- [x] Çalışan backend uygulaması
- [x] Docker Compose ortamı
- [x] PostgreSQL servisi
- [x] MongoDB servisi
- [x] Database connection testleri

### Acceptance Criteria

- [x] `docker compose up` ile servisler çalışır.
- [x] Frontend tarayıcıda açılır.
- [x] Backend health check endpoint'i çalışır.
- [x] Backend PostgreSQL'e bağlanabilir.
- [x] Backend MongoDB'ye bağlanabilir.

---

## Phase 2: Dataset Handling

### Goal

Kullanıcının CSV veya JSON dataset yükleyebilmesini, sample dataset seçebilmesini ve dataset'in sistem tarafından doğrulanmasını sağlamak.

### Tasks

- [x] CSV upload endpoint'i oluştur.
- [x] JSON upload endpoint'i oluştur.
- [x] Frontend dosya yükleme alanını oluştur.
- [x] CSV dosyalarında header row kontrolü yap.
- [x] CSV satırlarında kolon tutarlılığını doğrula.
- [x] JSON dosyalarında array of objects formatını doğrula.
- [x] JSON verisinin flat object structure kullandığını kontrol et.
- [x] Built-in sample dataset oluştur.
- [x] Frontend üzerinde sample dataset seçme butonu ekle.
- [x] Dataset metadata bilgisini üret:
  - Dataset ID
  - Dataset name
  - Record count
  - Fields
- [x] Geçersiz dataset durumları için açık hata mesajları göster.

### Deliverables

- [x] CSV upload API
- [x] JSON upload API
- [x] Sample dataset API
- [x] Dataset validation logic
- [x] Dataset metadata response
- [x] Frontend dataset upload section
- [x] Frontend dataset summary display

### Acceptance Criteria

- [x] Kullanıcı frontend üzerinden CSV dosyası yükleyebilir.
- [x] Kullanıcı frontend üzerinden JSON dosyası yükleyebilir.
- [x] Kullanıcı sample dataset seçebilir.
- [x] Sistem geçerli dataset'i kabul eder.
- [x] Sistem geçersiz dataset'i açık hata mesajı ile reddeder.
- [x] Dataset summary frontend üzerinde gösterilir.

---

## Phase 3: Data Loading

### Goal

Aynı dataset'in PostgreSQL ve MongoDB içine eşdeğer şekilde yüklenmesini sağlamak.

### Tasks

- [x] Backend içinde ortak dataset representation yapısını oluştur.
- [x] PostgreSQL için dataset table oluşturma mantığını geliştir.
- [x] MongoDB için dataset collection oluşturma mantığını geliştir.
- [x] CSV dataset kayıtlarını PostgreSQL'e yükle.
- [x] CSV dataset kayıtlarını MongoDB'ye yükle.
- [x] JSON dataset kayıtlarını PostgreSQL'e yükle.
- [x] JSON dataset kayıtlarını MongoDB'ye yükle.
- [x] Sample dataset kayıtlarını PostgreSQL'e yükle.
- [x] Sample dataset kayıtlarını MongoDB'ye yükle.
- [x] Benchmark öncesi geçici test verilerini temizleme mantığını oluştur.
- [x] PostgreSQL ve MongoDB kayıt sayılarının eşit olduğunu doğrula.

### Deliverables

- [x] PostgreSQL data loading service
- [x] MongoDB data loading service
- [x] Dataset preparation service
- [x] Temporary benchmark data cleanup logic

### Acceptance Criteria

- [x] Aynı dataset PostgreSQL ve MongoDB'ye yüklenir.
- [x] Her iki veritabanında da kayıt sayısı aynıdır.
- [x] Dataset yükleme işlemi tekrar çalıştırılabilir.
- [x] Yükleme hatalarında backend açık hata mesajı döndürür.

---

## Phase 4: Benchmark Engine

### Goal

WRITE, READ, UPDATE ve DELETE benchmark operasyonlarını PostgreSQL ve MongoDB üzerinde çalıştırmak.

### Tasks

- [x] Benchmark request modelini oluştur:
  - Dataset ID
  - Operation type
  - Record count
  - Repetitions
- [x] `POST /api/benchmarks/run` endpoint'ini oluştur.
- [x] WRITE benchmark operasyonunu PostgreSQL için uygula.
- [x] WRITE benchmark operasyonunu MongoDB için uygula.
- [x] READ benchmark operasyonunu PostgreSQL için uygula.
- [x] READ benchmark operasyonunu MongoDB için uygula.
- [x] UPDATE benchmark operasyonunu PostgreSQL için uygula.
- [x] UPDATE benchmark operasyonunu MongoDB için uygula.
- [x] DELETE benchmark operasyonunu PostgreSQL için uygula.
- [x] DELETE benchmark operasyonunu MongoDB için uygula.
- [x] Her operation için aynı record count değerini kullan.
- [x] Repetition logic ekle.
- [x] Benchmark sırasında execution time ölçümü yap.

### Deliverables

- [x] Benchmark run API
- [x] PostgreSQL WRITE, READ, UPDATE, DELETE runners
- [x] MongoDB WRITE, READ, UPDATE, DELETE runners
- [x] Repetition handling
- [x] Timing logic

### Acceptance Criteria

- [x] Kullanıcı frontend üzerinden benchmark operasyonu seçebilir.
- [x] Kullanıcı record count ve repetitions değerlerini belirleyebilir.
- [x] Sistem WRITE benchmark çalıştırabilir.
- [x] Sistem READ benchmark çalıştırabilir.
- [x] Sistem UPDATE benchmark çalıştırabilir.
- [x] Sistem DELETE benchmark çalıştırabilir.
- [x] Seçilen operasyon PostgreSQL ve MongoDB üzerinde aynı parametrelerle çalışır.
- [x] Backend benchmark sonucunu frontend'e döndürür.

---

## Phase 5: Metrics and Result Storage

### Goal

Benchmark sonuçları için performans metriklerini hesaplamak ve sonuçları daha sonra incelenebilecek şekilde saklamak.

### Tasks

- [x] Total execution time hesapla.
- [x] Average latency hesapla.
- [x] Throughput hesapla.
- [x] Minimum time hesapla.
- [x] Maximum time hesapla.
- [x] Standard deviation hesapla.
- [x] PostgreSQL ve MongoDB için aynı metric calculation formüllerini kullan.
- [x] Benchmark result modelini oluştur.
- [x] Benchmark result storage yapısını oluştur.
- [x] `GET /api/benchmarks` endpoint'ini oluştur.
- [x] `GET /api/benchmarks/{benchmark_id}` endpoint'ini oluştur.
- [x] Previous results listesini frontend'e döndür.

### Metrics

| Metric | Description |
| --- | --- |
| Total execution time | Benchmark operasyonunun toplam çalışma süresi |
| Average latency | Bir operasyon başına ortalama süre |
| Throughput | Saniye başına tamamlanan operasyon sayısı |
| Minimum time | Repetition sonuçları içindeki en hızlı çalışma süresi |
| Maximum time | Repetition sonuçları içindeki en yavaş çalışma süresi |
| Standard deviation | Repetition sonuçlarının kararlılığını gösteren değer |

### Deliverables

- [x] Metric calculation service
- [x] Benchmark result model
- [x] Result storage logic
- [x] Previous benchmark results API
- [x] Benchmark detail API

### Acceptance Criteria

- [x] Her benchmark sonucu PostgreSQL ve MongoDB metriklerini içerir.
- [x] Total execution time hesaplanır.
- [x] Average latency hesaplanır.
- [x] Throughput hesaplanır.
- [x] Minimum ve maximum time hesaplanır.
- [x] Standard deviation hesaplanır.
- [x] Benchmark sonuçları saklanır.
- [x] Önceki benchmark sonuçları API üzerinden alınabilir.

---

## Phase 6: Frontend Dashboard

### Goal

Kullanıcının dataset seçebildiği, benchmark parametrelerini ayarlayabildiği, benchmark çalıştırabildiği ve sonuçları görsel olarak karşılaştırabildiği ana dashboard ekranını oluşturmak.

### Tasks

- [x] Ana dashboard layout'unu oluştur.
- [x] Project title alanını ekle.
- [x] Dataset upload section oluştur.
- [x] CSV ve JSON dosya yükleme desteğini frontend'e ekle.
- [x] Sample dataset button ekle.
- [x] Uploaded dataset summary alanını oluştur.
- [x] Benchmark operation selector ekle:
  - WRITE
  - READ
  - UPDATE
  - DELETE
- [x] Benchmark record count bilgisini göster.
- [x] Repetitions input'u ekle.
- [x] Run Benchmark button ekle.
- [x] Loading state ekle.
- [x] Error state ekle.
- [x] PostgreSQL result card oluştur.
- [x] MongoDB result card oluştur.
- [x] Comparison table oluştur.
- [x] Total execution time chart ekle.
- [x] Throughput chart ekle.
- [x] Repeated runs line chart ekle.
- [x] Previous benchmark results table oluştur.

### Deliverables

- [x] Main dashboard
- [x] Dataset upload UI
- [x] Benchmark configuration form
- [x] PostgreSQL result card
- [x] MongoDB result card
- [x] Comparison table
- [x] Charts
- [x] Previous results table
- [x] Loading and error states

### Acceptance Criteria

- [x] Kullanıcı dataset yükleyebilir veya sample dataset seçebilir.
- [x] Kullanıcı benchmark operation seçebilir.
- [x] Sistem benchmark için aynı record count değerini kullanır.
- [x] Kullanıcı repetitions değerini girebilir.
- [x] Kullanıcı benchmark çalıştırabilir.
- [x] PostgreSQL ve MongoDB sonuçları ayrı kartlarda gösterilir.
- [x] Comparison table iki veritabanını yan yana gösterir.
- [x] Grafikler benchmark sonuçlarını görselleştirir.
- [x] Previous benchmark results table eski sonuçları gösterir.
- [x] Hata durumları frontend üzerinde açık şekilde gösterilir.

---

## Phase 7: Testing and Thesis Experiment

### Goal

Sistemin uçtan uca çalıştığını doğrulamak ve tez deneylerinde kullanılacak benchmark sonuçlarını üretmek.

### Tasks

- [ ] Docker Compose ile tüm sistemi çalıştır.
- [ ] Backend API endpoint'lerini test et.
- [ ] Frontend üzerinden dataset upload flow test et.
- [ ] Sample dataset flow test et.
- [ ] PostgreSQL data loading işlemini test et.
- [ ] MongoDB data loading işlemini test et.
- [ ] WRITE benchmark testleri çalıştır.
- [ ] READ benchmark testleri çalıştır.
- [ ] UPDATE benchmark testleri çalıştır.
- [ ] DELETE benchmark testleri çalıştır.
- [ ] Result cards ve comparison table çıktılarını kontrol et.
- [ ] Chart çıktılarının doğru veriyi gösterdiğini kontrol et.
- [ ] Previous results table çıktısını kontrol et.
- [ ] Geçersiz CSV ve JSON dosyalarıyla hata senaryolarını test et.
- [ ] PostgreSQL version bilgisini kaydet.
- [ ] MongoDB version bilgisini kaydet.
- [ ] Hardware specifications bilgisini kaydet.
- [ ] Tez için final benchmark sonuçlarını topla.
- [ ] Tez sonuç bölümü için tablo ve grafik verilerini hazırla.

### Deliverables

- [ ] Test edilmiş lokal Docker uygulaması
- [ ] Doğrulanmış benchmark flow
- [ ] Database version bilgileri
- [ ] Hardware specification notları
- [ ] Tez deneyleri için benchmark sonuçları
- [ ] Tez sonuç bölümünde kullanılabilecek tablo ve grafik verileri

### Acceptance Criteria

- [ ] Uygulama lokal Docker ortamında çalışır.
- [ ] Kullanıcı komut satırı kullanmadan benchmark çalıştırabilir.
- [ ] CSV dataset ile benchmark tamamlanır.
- [ ] JSON dataset ile benchmark tamamlanır.
- [ ] Sample dataset ile benchmark tamamlanır.
- [ ] PostgreSQL ve MongoDB sonuçları aynı arayüzde karşılaştırılır.
- [ ] Sonuçlar saklanır ve önceki sonuçlar görüntülenir.
- [ ] Sistem geçersiz inputlarda çökmeden hata gösterir.

---

## Scope Guard

Bu fazlar [PRD.md](PRD.md) dosyasındaki mevcut proje kapsamına göre hazırlanmıştır. Aşağıdaki konular bu fazların parçası değildir:

- Authentication
- Public deployment
- Multi-user support
- Concurrent workload testing
- Cloud database testing
- Distributed database testing
- Complex joins
- Advanced aggregation benchmarks
- Real-time load testing
- CPU or memory monitoring
