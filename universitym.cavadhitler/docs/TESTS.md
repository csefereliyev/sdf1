# Test ssenariləri və nəticələri

İşə salma: `python -m unittest discover -v`

**Ümumi nəticə: 36 test, 36 uğurlu, 0 uğursuz** (Python 3.13, Flask 3.1).

Aşağıda əsas ssenarilər verilib (tələb olunan minimum 5-dən çox). Qalan testlər `tests/` qovluğundadır.

| № | Ssenari | Növ | Gözlənilən nəticə | Test | Nəticə |
|---|---------|-----|-------------------|------|--------|
| T1 | Düzgün məlumatla tədbir yaratmaq | Normal | Tədbir bütün sahələrlə saxlanılır, qeydiyyat sayı 0 | `test_create_event_saves_all_fields` | ✅ |
| T2 | Məcburi sahələr boş | Xəta | `ValidationError`, boş sahələr siyahıda | `test_create_event_with_empty_required_fields_is_rejected` | ✅ |
| T3 | Keçmiş tarixə tədbir yaratmaq | Xəta | Rədd edilir | `test_create_event_in_past_is_rejected` | ✅ |
| T4 | Tutumu mövcud qeydiyyat sayından aşağı salmaq | Xəta | Rədd edilir, limit dəyişmir | `test_update_capacity_below_registered_count_is_rejected` | ✅ |
| T5 | Ada görə axtarış | Normal | Yalnız uyğun tədbir qayıdır | `test_search_by_name` | ✅ |
| T6 | Nəticəsiz axtarış | Sərhəd | Boş siyahı (UI-da "uyğun tədbir tapılmadı") | `test_empty_result_returns_empty_list` | ✅ |
| T7 | Axtarışda SQL injection cəhdi | Təhlükəsizlik | Cədvəl silinmir, nəticə boşdur | `test_sql_injection_attempt_is_harmless` | ✅ |
| T8 | Tədbirə qeydiyyat | Normal | İştirakçı sayı 1 artır | `test_register_increases_participant_count` | ✅ |
| T9 | Eyni tədbirə təkrar qeydiyyat | Xəta | `ConflictError`, say dəyişmir | `test_duplicate_registration_is_prevented` | ✅ |
| T10 | Limit dolduqdan sonra qeydiyyat | Xəta | `ConflictError`, say limiti aşmır | `test_capacity_limit_is_enforced` | ✅ |
| T11 | Qeydiyyatı ləğv edib başqasının yazılması | Normal | Yer boşalır, yeni qeydiyyat qəbul olunur | `test_cancel_frees_a_seat` | ✅ |
| T12 | Panel statistikası | Normal | Ümumi say, ən populyar tədbir, kateqoriya təhlili düzgün | `test_dashboard_statistics` | ✅ |
| T13 | Yanlış parolla giriş | Xəta | HTTP 401 | `test_login_with_wrong_password_returns_401` | ✅ |
| T14 | İcazələr: anonim / istifadəçi / admin | Təhlükəsizlik | 401 / 403 / 201 | `test_event_creation_permissions` | ✅ |
| T15 | Tam axın API üzərindən (frontend↔backend↔DB) | İnteqrasiya | Qeydiyyat → təkrar 409 → limit 409 → ləğv → yeni qeydiyyat 201 | `test_full_registration_flow` | ✅ |
| T16 | Gözlənilməyən server xətası | Xəta idarəsi | HTTP 500, anlaşıqlı mesaj, texniki detal gizli | `test_unexpected_error_returns_friendly_message` | ✅ |

## Əlavə yoxlamalar

- Parol bazada hash kimi saxlanılır (`test_password_is_hashed`).
- Tədbir silinəndə qeydiyyatlar da silinir (`test_delete_event_removes_its_registrations`).
- CSV ixracı və admin statistikası API-dən işləyir (`test_csv_export_and_stats`).
- Bütün səhifələr 200 qaytarır (`test_pages_render`).
- Real serverdə əl ilə yoxlama: `python seed.py` + `python run.py`, brauzerdə giriş, axtarış, qeydiyyat, panel.

## Əl ilə UI yoxlaması üçün çek-list (ekran görüntüləri üçün)

1. Ana səhifə — tədbirlər siyahısı, filtr paneli (`screenshots/01-events.png`)
2. Axtarışda nəticə yoxdur mesajı (`screenshots/02-empty-search.png`)
3. Qeydiyyat və limit dolu vəziyyəti (`screenshots/03-registration.png`)
4. Admin: tədbir yaratma/redaktə forması (`screenshots/04-event-form.png`)
5. Admin: idarəetmə paneli (`screenshots/05-dashboard.png`)
6. İştirakçı siyahısı və CSV ixrac (`screenshots/06-participants.png`)
