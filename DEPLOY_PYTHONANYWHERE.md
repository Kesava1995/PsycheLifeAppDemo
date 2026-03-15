# Deploying to PythonAnywhere

After pushing to GitHub and pulling on PythonAnywhere, do the following.

## 1. Environment variables (required)

Do **not** commit `.env` to git. On PythonAnywhere, set variables in the **Web** tab → **Code** → **Environment variables** (or in your WSGI file).

Add at least:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask secret (use a long random string in production) |
| `SYSTEM_EMAIL` | For “Forgot password” emails (e.g. your Gmail) |
| `SYSTEM_EMAIL_PASSWORD` | App password for that email |
| `CRON_SECRET` | Random string; used to protect the reminder cron URL (see below) |

Optional (defaults are fine for Gmail):

- `SYSTEM_SMTP_SERVER` (default: `smtp.gmail.com`)
- `SYSTEM_SMTP_PORT` (default: `587`)

For doctor-specific SMTP (reminders from each doctor’s email):

- `SMTP_ENCRYPTION_KEY` – only if you use a dedicated key for encrypting doctor app passwords (otherwise the app derives from `SECRET_KEY`).

## 2. Daily email reminders (8:00)

The in-process scheduler is **off** by default on PythonAnywhere so it doesn’t conflict with the worker.

**Option A – Use PythonAnywhere Tasks (recommended)**  
1. In the **Tasks** tab, add a daily task at 8:00 AM (or your timezone).  
2. Command example (replace `YOUR_CRON_SECRET` and your PythonAnywhere domain):

   ```bash
   curl "https://YOURUSER.pythonanywhere.com/cron/send_reminders?key=YOUR_CRON_SECRET"
   ```

   Use the same `CRON_SECRET` value you set in the Web app environment variables.

**Option B – Use the in-process scheduler**  
Set in the same environment variables:

- `RUN_SCHEDULER=1`

Then the app will run the daily reminder job itself at 8:00 (less reliable on free/hobby hosting than Option A).

## 3. Reload the app

After changing env vars or code, in the **Web** tab click **Reload** for your app.

## 4. Checklist

- [ ] Env vars set (no `.env` in repo): `SECRET_KEY`, `SYSTEM_EMAIL`, `SYSTEM_EMAIL_PASSWORD`, `CRON_SECRET`
- [ ] Virtualenv has dependencies: `pip install -r requirements.txt`
- [ ] WSGI points to your app (e.g. `from app import app`)
- [ ] Either a daily Task calling `/cron/send_reminders?key=...` or `RUN_SCHEDULER=1`
- [ ] Reload the Web app after any change
