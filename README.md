# Attendance Script

Marks daily class attendance. Everyone is Present by default; you give only the
Sn. numbers of absent students. Works on macOS and Ubuntu with Brave browser.

## Setup (once)

```
python3 -m venv .venv && source .venv/bin/activate && pip install playwright
cp .env.example .env
```

Edit `.env`:

```
URL=your_portal_login_url
LOGIN_ID=your_login_id
PASSWORD=your_password
```

## Run

```
source .venv/bin/activate && python mark.py 27 29 32
```

`27 29 32` = Sn. numbers of absent students. Leave them out if everyone is present.

If login is needed, wait for the verification to succeed, then press Enter.

## Notes

- Never commit `.env`, `.venv/` or `attendance.png`.
- If a Sn. number is not found, or the summary counts do not match, nothing is saved.
