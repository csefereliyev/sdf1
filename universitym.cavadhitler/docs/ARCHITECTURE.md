# Arxitektura və texnologiya seçimləri

## Ümumi sxem

```
Brauzer (HTML + JS)  ──fetch/JSON──▶  routes.py  ──▶  services.py  ──▶  repositories.py  ──▶  SQLite
   istifadəçi interfeysi              HTTP qatı       biznes məntiqi      SQL qatı             məlumat
```

Tələb olunan əlaqə: **frontend** (JS) `/api/...` sorğuları göndərir → **backend** (Flask) yoxlayır və biznes qaydalarını tətbiq edir → **database** (SQLite) məlumatı saxlayır.

## Texnologiya seçimləri və əsaslandırma

| Seçim | Səbəb | Alternativ və niyə seçilmədi |
|-------|-------|------------------------------|
| **Python + Flask** | Kiçik, aydın, az "sehr"; hər sətirin nə etdiyini izah etmək asandır. REST API və HTML-i eyni layihədə verir. | Django — güclüdür, amma ORM/admin çox işi gizlədir, müdafiədə izah çətinləşir. Node/Express — eyni dərəcədə uyğundur, Python seçildi. |
| **SQLite** | Ayrıca server tələb etmir, layihə ilə birlikdə işləyir, tam SQL, xarici açar və tranzaksiya dəstəyi var. | PostgreSQL/MySQL — istehsal üçün daha yaxşıdır, amma bu miqyasda quraşdırma yükü artırır. Struktur başqa DBMS-ə asan keçirilə bilər. |
| **Xalis `sqlite3` + Repository** | SQL və parametrli sorğular açıq görünür, təhlükəsizlik yoxlanıla bilir. | ORM (SQLAlchemy) — əlavə asılılıq və abstraksiya. |
| **Jinja2 + Vanilla JS** | Build addımı yoxdur, asılılıq azdır; JS ilə API çağırışları frontend↔backend əlaqəsini aydın göstərir. | React/Vue — bu həcm üçün lazımsız mürəkkəblik. |
| **`unittest`** | Python ilə gəlir, əlavə quraşdırma tələb etmir. | pytest — rahatdır, `unittest` testləri onunla da işləyir. |
| **Git** | Versiya tarixçəsi və qarşılıqlı iş. | – |

## Qatlar və məsuliyyətlər (OOP, SOLID)

- **`routes.py`** — yalnız HTTP: JSON oxuyur, icazəni yoxlayır (`login_required`, `admin_required`), servisi çağırır.
- **`services.py`** — biznes qaydaları: yoxlamalar (`EventInput`), limit və təkrar qeydiyyat qaydaları, statistika. SQL bilmir.
- **`repositories.py`** — yalnız SQL. Hər sinif bir cədvəl/məsələ üçündür.
- **`db.py`** — bağlantı və tranzaksiya.
- **`errors.py`** — xəta ierarxiyası; HTTP statusu xətanın özündə saxlanılır.

SOLID tətbiqi:
- **S (Single Responsibility):** hər sinif bir məsuliyyət daşıyır (`AuthService`, `EventService`, `RegistrationService`, `StatsService`, ayrı repository-lər).
- **O (Open/Closed):** yeni xəta növü və ya yeni axtarış filtri mövcud kodu pozmadan əlavə olunur (xəta sinifləri `AppError`-dan törəyir; yeni filtr yalnız `search` içində şərt əlavə edir).
- **D (Dependency Inversion/Injection):** servislər bağlantını və `clock` funksiyasını konstruktordan alır — testdə yaddaşdakı baza və sabit tarix verilir.
- Təkrar kodun azaldılması: bütün xətalar bir mərkəzi error handler-də emal olunur, `_present` bütün tədbir cavablarını eyni formada hazırlayır.

## Təhlükəsizlik

- SQL injection: yalnız parametrli sorğular.
- Parollar `werkzeug.security` ilə hash olunur; giriş xətasında "e-poçt, yoxsa parol yanlışdır" ayırd edilmir.
- Rol yoxlaması serverdə aparılır (frontend gizlətməsinə etibar edilmir).
- XSS: frontend istifadəçi məlumatını `esc()` ilə escape edir.
- CSRF: cookie `SameSite=Lax` + dəyişdirici sorğular yalnız `application/json` qəbul edir.
- CSV injection: ixrac zamanı `=`, `+`, `-`, `@` ilə başlayan xanalar neytrallaşdırılır.
- Gözlənilməyən xəta: istifadəçiyə ümumi mesaj göstərilir, texniki detal yalnız loqda qalır.

## Məlum məhdudiyyətlər

- SQLite eyni anda çoxlu yazı sorğusu üçün nəzərdə tutulmayıb; böyük yük üçün PostgreSQL tövsiyə olunur.
- Tətbiq `debug=True` ilə yalnız inkişaf üçün işə salınır; istehsalda Gunicorn/Waitress və güclü `SECRET_KEY` istifadə edin.
- Parol sıfırlama və e-poçt təsdiqi yoxdur.
