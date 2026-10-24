# Universitet Tədbirlərinin İdarə Edilməsi və Qeydiyyat Sistemi

Fənn: **Proqramlaşdırma texnologiyaları**

Universitetdə keçirilən konfrans, seminar, təlim və müsabiqələrin idarə olunması üçün web tətbiqi:
tədbirlərin yaradılması, axtarışı, iştirakçı qeydiyyatı və statistik panel.

## Texnologiyalar

| Hissə | Seçim |
|-------|-------|
| Backend | Python 3 + Flask (REST API) |
| Database | SQLite (`sqlite3`, parametrli sorğular) |
| Frontend | Jinja2 şablonları + Vanilla JavaScript (`fetch`) + CSS |
| Testlər | `unittest` (36 test) |
| Versiya nəzarəti | Git |

Seçimlərin əsaslandırılması: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Quraşdırma və işə salma

```bash
git clone <repo-url>
cd university-event-management

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                   # (ixtiyari) demo məlumatlar
python run.py                    # http://127.0.0.1:5000
```

Verilənlər bazası ilk işə salınmada avtomatik yaradılır (`instance/events.db`).

**Standart hesablar**

| Rol | E-poçt | Parol |
|-----|--------|-------|
| Administrator | `admin@university.az` | `Admin123!` |
| İstifadəçi (seed ilə) | `student1@university.az` | `Student123!` |

> Real istifadədə `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` mühit dəyişənləri ilə dəyişdirin.

## Testlərin işə salınması

```bash
python -m unittest discover -v
```

Test ssenariləri: [docs/TESTS.md](docs/TESTS.md)

## Funksiyalar

- **Tədbirlər:** yaratma, redaktə, silmə, siyahı, keçmiş/gələcək fərqləndirilməsi (yalnız admin dəyişir)
- **Axtarış:** ada, kateqoriyaya, yerə, tarixə və tarix aralığına görə; nəticə yoxdursa mesaj
- **Qeydiyyat:** tədbirə yazılma, təkrar qeydiyyatın və limit aşımının qarşısı, ləğv etmə, iştirakçı sayı
- **Panel (admin):** tədbir və qeydiyyat sayı, ən populyar tədbirlər, kateqoriyalar üzrə təhlil
- **Təhlükəsizlik:** parametrli SQL, parol hash-i, rol yoxlaması, XSS escape, CSV injection qorunması
- **Fərdi əlavə funksiya (nümunə):** iştirakçı siyahısının CSV-yə ixracı və tutum dəyişəndə limitin yenidən yoxlanılması

## Layihə strukturu

```
app/
  __init__.py       # tətbiq fabriki, xəta idarəetməsi
  config.py         # konfiqurasiya
  db.py             # bağlantı, sxem, tranzaksiya
  schema.sql        # cədvəllər
  errors.py         # xüsusi xəta sinifləri
  repositories.py   # SQL qatı
  services.py       # biznes məntiqi və yoxlamalar
  routes.py         # REST API və səhifələr
  templates/        # HTML (Jinja2)
  static/           # CSS, JavaScript
tests/              # unit və inteqrasiya testləri
docs/               # DB, arxitektura, testlər, AI jurnalı
screenshots/        # ekran görüntüləri
seed.py             # demo məlumatlar
run.py              # giriş nöqtəsi
```

## API icmalı

| Metod | Yol | Giriş |
|-------|-----|-------|
| POST | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | – |
| GET | `/api/auth/me`, `/api/categories` | – |
| GET | `/api/events?q=&category_id=&location=&date=&date_from=&date_to=&status=` | – |
| GET | `/api/events/<id>` | – |
| POST / PUT / DELETE | `/api/events`, `/api/events/<id>` | admin |
| POST / DELETE | `/api/events/<id>/register` | istifadəçi |
| GET | `/api/events/<id>/participants`, `/api/events/<id>/export` | admin |
| GET | `/api/stats` | admin |
