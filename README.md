# Vibe Electrician

Εσωτερική web εφαρμογή για καταχώρηση εσόδων/εξόδων ανά έργο ηλεκτρολογικών εγκαταστάσεων, με reports και export.

## Χαρακτηριστικά

- Καταχώρηση **έργων**, **εσόδων** και **εξόδων**
- Dashboard, ημερολόγιο, προσφορές, λειτουργικά έξοδα
- Μηνιαία αναφορά με trend 6 μηνών
- Export **Excel** και **PDF**
- Django Admin
- **Docker-ready** — self-hosted (Tailscale / reverse proxy optional)

---

## Γρήγορη εκκίνηση με Docker (προτεινόμενο)

```bash
git clone <repo-url> vibe-electrician
cd vibe-electrician

cp .env.example .env
# Άλλαξε DJANGO_SECRET_KEY στο .env (δες παρακάτω)

docker compose up -d --build
```

Άνοιξε http://localhost:8000

**Πρώτος χρήστης (admin):**

```bash
docker compose exec web python manage.py createsuperuser
```

Μετά το login: **Ρυθμίσεις** → συμπλήρωσε στοιχεία εταιρείας (για PDF προσφορών).

### Secret key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Βάλε το αποτέλεσμα στο `.env` ως `DJANGO_SECRET_KEY=...`

### Χρήσιμες εντολές

```bash
docker compose logs -f web          # logs
docker compose down                 # stop
docker compose up -d --build        # rebuild μετά από git pull
docker compose exec web python manage.py migrate
```

### Production stack (app + Portainer)

Στον server (Hetzner + Tailscale):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

- Εφαρμογή: `http://100.x.x.x:8000` (Tailscale IP)
- Portainer: `https://100.x.x.x:9443`

### Demo δεδομένα (μόνο dev)

Στο `.env` βάλε `SEED_DEMO=true` και ξανακάνε `docker compose up -d --build`.

| Χρήστης | Κωδικός | Ρόλος |
|---------|---------|-------|
| partner1 | demo1234 | Χρήστης |
| partner2 | demo1234 | Χρήστης |
| admin | admin1234 | Superuser |

**Μην** χρησιμοποιείς `SEED_DEMO=true` σε παραγωγή.

---

## Τοπική ανάπτυξη (χωρίς Docker)

```bash
pip install -r requirements.txt
mkdir data

# Προαιρετικά: cp .env.example .env και DJANGO_DEBUG=true
python manage.py migrate
python manage.py seed_demo          # προαιρετικό
python manage.py collectstatic --noinput
python manage.py runserver
```

---

## Μεταβλητές περιβάλλοντος (`.env`)

| Μεταβλητή | Περιγραφή |
|-----------|-----------|
| `DJANGO_SECRET_KEY` | **Υποχρεωτικό** σε production |
| `DJANGO_DEBUG` | `false` σε production (default στο compose) |
| `DJANGO_ALLOWED_HOSTS` | Hostnames/IPs, χωρισμένα με κόμμα |
| `CSRF_TRUSTED_ORIGINS` | HTTPS origins αν έχεις reverse proxy |
| `SEED_DEMO` | `true` μόνο για demo |
| `WEB_PORT` | Θύρα host (default `8000`) |
| `COMPANY_*` | Fallback για PDF (κύρια ρύθμιση από admin) |

Δεδομένα (SQLite + uploads) αποθηκεύονται στο `./data/` (Docker volume).

---

## Tailscale / Hetzner (αργότερα)

Για πρόσβαση μόνο μέσω VPN, χωρίς άνοιγμα port στο router:

```bash
# 1. Bind μόνο στο localhost
docker compose -f docker-compose.yml -f docker-compose.tailscale.yml up -d

# 2. Στο host (μετά το tailscale up)
tailscale serve --bg http://127.0.0.1:8000
```

Στο `.env` πρόσθεσε στα `DJANGO_ALLOWED_HOSTS` το hostname/IP της μηχανής και:

```
CSRF_TRUSTED_ORIGINS=https://your-machine.your-tailnet.ts.net
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

Σημείωση: στο Django χρησιμοποίησε `.ts.net` (όχι `*.ts.net`) για subdomain matching.

---

## Backup

```bash
./scripts/backup.sh ./data/db.sqlite3 ./backups
```

Cron παράδειγμα (nightly):

```bash
0 3 * * * /path/to/vibe-electrician/scripts/backup.sh /path/to/vibe-electrician/data/db.sqlite3 /path/to/backups
```

---

## Δομή project

```
Vibe-Electrician/
├── projects/              # Models, views, admin
├── reports/               # Excel/PDF export
├── templates/             # HTML (ελληνικά)
├── static/                # CSS, JS
├── data/                  # SQLite + media (gitignored, Docker volume)
├── scripts/backup.sh
├── docker-compose.yml
├── docker-compose.tailscale.yml   # optional overlay
├── Dockerfile
└── .env.example
```

---

## Tech stack

- Python 3.12 + Django 5
- SQLite
- WeasyPrint (PDF), openpyxl (Excel)
- WhiteNoise + Gunicorn
- Docker Compose
