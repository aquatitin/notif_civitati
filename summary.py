"""Resum diari: quantes comprovacions s'han fet avui (hora de Madrid),
quantes han anat bé o han fallat, i com està ara la disponibilitat."""
import json
import os
import urllib.request
from datetime import datetime, time
from zoneinfo import ZoneInfo

import check  # reutilitza get_calendar, hours_for, notify i TARGET_DATES

TZ = ZoneInfo("Europe/Madrid")
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]


def runs_today():
    start_local = datetime.combine(datetime.now(TZ).date(), time(0, 0), TZ)
    start_utc = start_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs, page = [], 1
    while True:
        url = (
            f"https://api.github.com/repos/{REPO}/actions/workflows/check.yml/runs"
            f"?created=%3E%3D{start_utc}&per_page=100&page={page}"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.load(r)["workflow_runs"]
        runs += batch
        if len(batch) < 100:
            return runs
        page += 1


def current_status():
    try:
        cal = check.get_calendar()
    except Exception as e:  # noqa: BLE001
        return [f"No s'ha pogut consultar ara ({e.__class__.__name__})"]
    dates = {d.get("date"): d for d in cal.get("dates", [])}
    lines = []
    for target in check.TARGET_DATES:
        day = dates.get(target)
        if day is None:
            lines.append(f"{target}: sense disponibilitat")
        else:
            hours = check.hours_for(cal, day)
            lines.append(f"{target}: DISPONIBLE ({'; '.join(hours) or 'horari no indicat'})")
    return lines


def main():
    runs = runs_today()
    ok = sum(1 for r in runs if r.get("conclusion") == "success")
    ko = sum(1 for r in runs if r.get("conclusion") == "failure")
    other = len(runs) - ok - ko
    status = current_status()
    available = any("DISPONIBLE" in s for s in status)

    msg = [
        f"Comprovacions avui: {len(runs)}",
        f"  - correctes: {ok}",
        f"  - amb error: {ko}",
    ]
    if other:
        msg.append(f"  - altres (en curs/cancel·lades): {other}")
    msg.append("")
    msg.append("Estat ara:")
    msg += [f"  {s}" for s in status]
    text = "\n".join(msg)
    print(text)

    req = urllib.request.Request(
        f"https://ntfy.sh/{check.NTFY_TOPIC}",
        data=text.encode("utf-8"),
        headers={
            "Title": "Resum diari free tour Breslau",
            "Priority": "high" if available else "default",
            "Tags": "tada" if available else "clipboard",
            "Click": check.PAGE_URL,
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30)


if __name__ == "__main__":
    main()
