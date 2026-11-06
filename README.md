# Attendance Script

Marks daily class attendance. Everyone is Present by default; you give only the
Sn. numbers of absent students. Works with Brave browser.

## Setup (once)

```
python3 -m venv .venv && source .venv/bin/activate && pip install playwright
```

## Run

```
source .venv/bin/activate && python mark.py 27 29 32
```

`27 29 32` = Sn. numbers of absent students. Leave them out if everyone is present.


## Notes

- If a Sn. number is not found, or the summary counts do not match, nothing is saved.
