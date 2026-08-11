# LLM Evaluation Lab

LLM konfigürasyonlarını değerlendirip karşılaştırmak için yerel (local) bir
platform — bir QA (soru-cevap) veri setini [Ollama](https://ollama.com)
üzerinden farklı modeller ve prompt'larla çalıştırır, her cevabı puanlar ve
konfigürasyonları yan yana karşılaştırır (ör. güçlü bir model vs. zayıf bir
model, ya da bir prompt vs. başka bir prompt).

Python ile uçtan uca yazıldı (FastAPI + PostgreSQL + SQLAlchemy/Alembic +
Gradio), tamamen yerel — dışarıya bağlı bir LLM API'si veya bulut bağımlılığı
yok. Her şey yerel bir Ollama sunucusuna ve Docker'lanmış bir Postgres
örneğine karşı çalışır.

## Neden bu proje

Portföyümdeki önceki tüm projeler gerçekten bilmediğim bir stack'te
(TypeScript/Next.js) kurulmuştu ve kodun büyük kısmı AI tarafından
yazılmıştı — yani mülakatta o kodu gerçek anlamda savunamıyordum. Bu proje
tam tersi: baştan sona Python ile, gerçekten öğrendiğim bir stack'te, teknoloji
teknoloji inşa edildi. Tüm build boyunca uyduğum kural şuydu: **projenin o
anda gerçek bir sorunu çözmedikçe hiçbir teknoloji eklenmez** — örneğin
FastAPI, API'yi dışarı açmak için gerçek bir sebep oluşana kadar
eklenmedi; `pandas` da karşılaştırma adımı gerçek tablosal (tabular)
agregasyona ihtiyaç duyana kadar eklenmedi.

## Özellikler

- **Veri seti yönetimi** — düz bir JSON listesi (soru/beklenen-cevap
  çiftleri) tekrar kullanılabilir bir dataset olarak içeri aktarılır.
- **Yapılandırılabilir deneyler (experiments)** — bir dataset'i bir model
  konfigürasyonu (Ollama modeli + parametreler) ve bir prompt şablonuyla
  eşleştirir; aynı konfigürasyonu daha sonra tekrar çalıştırıp zaman
  içindeki run'ları karşılaştırmak mümkündür.
- **Ollama'ya karşı LLM çalıştırma** — her test case için yerel bir Ollama
  modelini çağırır; cevap metnini, gecikmeyi (latency) ve prompt/completion
  token sayılarını kaydeder. Tek bir başarısız çağrı tüm run'ı iptal etmez.
- **Deterministik puanlama** — exact-match ve normalized-similarity
  evaluator'ları her cevabı beklenen cevaba göre puanlar.
- **Yan yana karşılaştırma** — iki veya daha fazla run arasında başarı
  oranı, gecikme, token kullanımı ve metrik başına ortalama skor agregasyonu
  (`pandas` ile).
- **REST API** — dataset → experiment → run → evaluate → compare akışının
  tamamı FastAPI üzerinden dışarı açılmış ve Swagger UI ile belgelenmiştir.
- **Demo arayüzü** — Swagger'la uğraşmadan tüm akışı (dataset, iki model ve
  bir prompt seçip tek butona basarak) çalıştıran bir Gradio sayfası.

## Mimari

```
┌─────────────┐        ┌──────────────┐        ┌───────────────────┐
│  Gradio UI   │ ─────▶ │   FastAPI    │ ─────▶ │  PostgreSQL (16)   │
│ (port 7860)  │  HTTP  │ (port 8000)  │  SQL   │  Docker Compose    │
└─────────────┘        └──────┬───────┘        └───────────────────┘
                               │ HTTP
                               ▼
                        ┌──────────────┐
                        │    Ollama     │
                        │ (host, 11434) │
                        └──────────────┘
```

- **FastAPI**, düz fonksiyonların üzerinde ince bir HTTP katmanıdır — her
  router, SQLAlchemy `Session` alan bir repository/runner/evaluator/
  comparison fonksiyonunu sarmalar. İş mantığının hiçbiri router'ların
  içinde yaşamaz.
- **Ollama host makinede çalışır**, container içinde değil — FastAPI
  container'ı ona `host.docker.internal` üzerinden ulaşır; bu, bir
  geliştiricinin container'lı bir backend'in yanında yerel inference'ı
  gerçekte nasıl çalıştıracağını yansıtır.
- **Gradio ayrı bir process'tir**, yalnızca FastAPI HTTP API'siyle konuşur
  (`httpx` üzerinden) — kendi skorlama/agregasyon mantığı yoktur ve dataset,
  model config veya prompt oluşturamaz (yalnızca var olan satırlar,
  dropdown'dan seçilir).

## Nasıl çalışır

1. **İçeri aktar (import)** — düz bir JSON dosyasındaki
   `{question, expected_answer}` çiftlerini CLI ile bir dataset'e aktar.
2. **Yapılandır** — bir model (Ollama model adı + opsiyonel parametreler) ve
   bir prompt şablonu tanımla.
3. **Bir experiment oluştur** — dataset + model config + prompt'un tekrar
   kullanılabilir bir eşleşmesi.
4. **Çalıştır (run)** — her test case'in sorusu prompt şablonuna gömülüp
   Ollama'ya gönderilir; cevap, gecikme ve token sayıları her test case için
   bir `ExperimentRun` olarak kaydedilir.
5. **Değerlendir (evaluate)** — her cevap, exact-match ve
   normalized-similarity evaluator'larıyla beklenen cevaba göre puanlanır.
6. **Karşılaştır (compare)** — iki veya daha fazla run arasında başarı
   oranı, gecikme, token ve metrik başına ortalama skoru agregasyonla
   karşılaştırarak hangi konfigürasyonun gerçekten daha iyi performans
   gösterdiğini gör.

## Teknoloji yığını

| Katman | Teknoloji |
|---|---|
| Dil | Python 3.12 |
| Paket/ortam yöneticisi | [`uv`](https://docs.astral.sh/uv/) (src-layout paket) |
| Web API | FastAPI + Uvicorn |
| Veritabanı | PostgreSQL 16 (Docker Compose) |
| ORM / migration | SQLAlchemy 2.0 (tipli `Mapped[...]` stili) + Alembic |
| LLM backend | [Ollama](https://ollama.com), `httpx` ile doğrudan HTTP üzerinden |
| Veri agregasyonu | `pandas` (yalnızca karşılaştırma adımında) |
| Demo arayüzü | Gradio |
| Test | `pytest`, gerçek bir Postgres'e karşı transactional-rollback fixture'ları |
| Containerization | Docker + Docker Compose (multi-stage build) |

LangChain yok, RAG yok, agent/tool-calling yok, LLM-as-a-judge yok — bu
bilinçli olarak kapsamı sınırlandırılmış bir V1. Bunlar gerçek, ayrıca
planlanmış V2 fikirleri; sadece daha uzun bir teknoloji listesi için
eklenmiş şeyler değil.

## Proje yapısı

```
llm-eval-lab/
├── src/llm_eval_lab/
│   ├── models/        # SQLAlchemy ORM modelleri
│   ├── schemas/        # Pydantic DTO'lar (ORM modellerinden ayrı)
│   ├── datasets/        # dataset repository + JSON dosya loader'ı
│   ├── experiments/     # model_config / prompt / experiment repository
│   ├── llm/              # LLMClient protokolü, Ollama client, provider factory
│   ├── runner/           # experiment runner (bir run'ı bir LLM'e karşı çalıştırır)
│   ├── evaluation/       # Evaluator protokolü + deterministik evaluator'lar
│   ├── comparison/       # pandas tabanlı run karşılaştırma/agregasyon
│   ├── api/               # FastAPI app, router'lar, dependency wiring
│   ├── ui/                # Gradio demo app + kendi ince API client'ı
│   └── cli/                # argparse entrypoint'leri (import, run, evaluate, compare)
├── migrations/            # Alembic migration'ları
├── tests/                  # pytest suite (unit + integration)
├── data/sample_datasets/    # qa_smoke_test.json — tüm süreçte kullanılan fixture dataset
├── docker-compose.yml       # db + app servisleri
└── Dockerfile                # FastAPI app için multi-stage build
```

## Kurulum

### Ön koşullar

- Python 3.12+ ve [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Docker Desktop (PostgreSQL için, ve isteğe bağlı olarak container'lı API için)
- [Ollama](https://ollama.com/download), yerel olarak çalışıyor ve her iki
  model de indirilmiş olmalı:

```bash
ollama pull qwen2.5:7b
ollama pull llama3.2:3b
```

### 1. Bağımlılıkları kur

```bash
uv sync
```

### 2. Ortam değişkenlerini ayarla

```bash
cp .env.example .env
```

Varsayılan değerler zaten aşağıdaki Docker Compose kurulumuyla eşleştiği
için standart bir yerel çalıştırma için düzenleme gerekmez.

### 3. PostgreSQL'i başlat

```bash
docker compose up -d db
```

### 4. Veritabanı migration'larını çalıştır

```bash
uv run alembic upgrade head
```

### 5. Örnek dataset'i içeri aktar

```bash
uv run python -m llm_eval_lab.cli.import_dataset data/sample_datasets/qa_smoke_test.json --name "QA Smoke Test"
```

### 6. API'yi çalıştır

```bash
uv run uvicorn llm_eval_lab.api.main:app --reload
```

Swagger UI: **http://localhost:8000/docs**

### 7. Gradio demo arayüzünü çalıştır

Ayrı bir terminalde (FastAPI zaten çalışıyor olmalı):

```bash
uv run python -m llm_eval_lab.ui.gradio_app
```

**http://localhost:7860** adresinde açılır.

### Alternatif: API'yi container'lı çalıştırma

```bash
docker compose up --build -d      # db + app'i başlatır
docker compose run --rm app alembic upgrade head
```

Gradio arayüzü yine yerelde çalıştırılır
(`uv run python -m llm_eval_lab.ui.gradio_app`), container'lı API'ye karşı —
kendisi container'lanmamıştır.

## Örnek: gerçek değerlendirme çıktısı

`uv run python -m llm_eval_lab.cli.compare_runs <run_id_a> <run_id_b>`
komutunun gerçek çıktısı — aynı 10 soruluk dataset ve aynı prompt üzerinde
`qwen2.5:7b` ile bilinçli olarak daha zayıf tutulan `llama3.2:3b`'nin, yerel
olarak çalışan bir Ollama sunucusuna karşı karşılaştırılması:

```
Run 124 - UI Demo - Qwen 2.5 7B - QA Model Comparison - Concise QA Prompt (qwen2.5:7b)
  success_rate=100.0% (10/10)
  avg_latency_ms=591.3
  avg_prompt_tokens=45.6  avg_completion_tokens=7.8
  exact_match: avg=0.300
  normalized_similarity: avg=0.598

Run 125 - UI Demo - Llama 3.2 3B - QA Model Comparison - Concise QA Prompt (llama3.2:3b)
  success_rate=100.0% (10/10)
  avg_latency_ms=466.3
  avg_prompt_tokens=41.5  avg_completion_tokens=15.8
  exact_match: avg=0.000
  normalized_similarity: avg=0.303
```

Daha güçlü model (`qwen2.5:7b`) her iki metrikte de daha yüksek skor
alıyor — özenle seçilmiş bir örnek değil, gerçek ve tekrarlanabilir bir fark.
Aynı karşılaştırma `GET /compare?run_ids=124&run_ids=125` üzerinden veya
Gradio arayüzünden de erişilebilir.

## API

API çalışırken **`/docs`** adresinde tam interaktif dokümantasyon
(request/response şemaları, try-it-out) mevcuttur. Ana endpoint'lerin özeti:

| Method | Path | Açıklama |
|---|---|---|
| `POST` | `/datasets` | Dataset oluştur |
| `GET` | `/datasets` | Dataset'leri listele |
| `GET` | `/datasets/{id}` | Bir dataset'i test case'leriyle birlikte getir |
| `PATCH` / `DELETE` | `/datasets/{id}` | Dataset güncelle / sil |
| `POST` / `GET` | `/model-configs` | Model config oluştur / listele (Ollama modeli + parametreler) |
| `POST` / `GET` | `/prompts` | Prompt şablonu oluştur / listele |
| `POST` / `GET` | `/experiments` | Experiment oluştur / listele (dataset + model config + prompt) |
| `GET` | `/experiments/{id}` | Tek bir experiment'i getir |
| `POST` | `/experiments/{id}/runs` | Experiment'i Ollama'ya karşı **çalıştır** (senkron) |
| `GET` | `/runs/{id}` | Bir run'ı cevapları ve değerlendirme skorlarıyla getir |
| `POST` | `/runs/{id}/evaluate` | Bir run'ın cevaplarını puanla (exact-match + normalized-similarity) |
| `GET` | `/compare?run_ids=...` | İki veya daha fazla run'ı karşılaştır (tekrarlanabilir query param) |

Not: Dataset **import** işlemi (bir JSON dosyasından test case yükleme)
bilinçli olarak yalnızca CLI üzerinden yapılır — bu bir dosya yükleme
meselesidir, API'nin dışarı açması gereken bir şey değildir.

## Gradio arayüzünü kullanma

1. **http://localhost:7860** adresini aç.
2. Dropdown'dan bir **Dataset** seç.
3. **Model A** ve **Model B**'yi seç — karşılaştırılacak iki konfigürasyon.
4. Bir **Prompt** şablonu seç.
5. **Run Comparison**'a tıkla. Status kutusu ilerlemeyi akış halinde gösterir
   (experiment'ler hazırlanıyor → Model A çalışıyor → Model B çalışıyor →
   değerlendiriliyor → karşılaştırılıyor → tamamlandı) ve sonuç tablosu her
   iki model için başarı oranı, ortalama gecikme, ortalama token ve metrik
   başına ortalama skorla dolar.
6. **Refresh dropdowns**, API'den güncel listeleri yeniden çeker — başka
   yerden yeni dataset/config/prompt oluşturduktan sonra faydalıdır.

Arayüz kendisi asla dataset, model config veya prompt oluşturmaz — yalnızca
var olan satırlar (CLI veya API üzerinden oluşturulmuş) seçilebilir.

## Testleri çalıştırma

```bash
uv run pytest                # sadece unit testler (hızlı, canlı Ollama gerekmez)
uv run pytest -m integration  # gerçek yerel Ollama'ya karşı çalışan testler dahil
```

## Kapsam

Bu bilinçli olarak sınırlandırılmış bir V1'dir: dataset yönetimi, Ollama
çalıştırma, deterministik değerlendirme, karşılaştırma, bir REST API ve bir
demo arayüzü — uçtan uca, hiçbir şey yarım bırakılmadan. RAG, LangChain,
LLM-as-a-judge ve agent/tool-calling değerlendirmesi ayrıca planlanmış
gerçek V2 fikirleridir, burada yer almazlar.
