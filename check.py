"""Comprova si el free tour de Breslau (Civitatis, activitat 5054) té
disponibilitat el dia indicat i, si en té, envia un avís per ntfy.sh."""
import json
import os
import sys
import urllib.request

ACTIVITY_ID = "5054"
# Una o més dates separades per comes, p. ex. "2026-11-26,2026-11-29"
TARGET_DATES = [
    d.strip()
    for d in os.environ.get("TARGET_DATE", "2026-11-26,2026-11-29").split(",")
    if d.strip()
]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]  # secret del repositori
PAGE_URL = "https://www.civitatis.com/es/breslavia/visita-guiada-breslavia/"
API_URL = (
    f"https://www.civitatis.com/pdp/api/activities/{ACTIVITY_ID}/calendar"
    f"?lang=es&currency=EUR&activityId={ACTIVITY_ID}"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": PAGE_URL,
}


def get_calendar():
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["calendar"]


def hours_for(cal, day):
    """Retorna els horaris i modalitats del dia (p. ex. '10:30 Tour en español')."""
    rate_ids = set()
    for ids in day.get("allRateIds", {}).values():
        rate_ids.update(ids)
    out = []
    for rate in cal.get("rates", []):
        if rate.get("id") in rate_ids:
            for h in rate.get("hours", []):
                mods = ", ".join(m.get("name", "") for m in h.get("modalities", []))
                out.append(f"{h.get('time')} ({mods})" if mods else h.get("time"))
    return out


def notify(title, msg):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "high",
            "Tags": "tada",
            "Click": PAGE_URL,
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30)


def main():
    cal = get_calendar()
    dates = cal.get("dates", [])
    if not dates:
        # Si la resposta ve buida, probablement ens han bloquejat: falla perquè ho vegis.
        sys.exit("Resposta sense dates: possible bloqueig o canvi a l'API")
    found = []
    for target in TARGET_DATES:
        day = next((d for d in dates if d.get("date") == target), None)
        if day is None:
            print(f"{target}: sense disponibilitat")
            continue
        hours = hours_for(cal, day)
        detail = "; ".join(hours) if hours else "horari no indicat"
        print(f"{target}: DISPONIBLE -> {detail}")
        found.append(f"{target}: {detail}")
    if found:
        notify(
            "Free tour Breslau: hi ha places!",
            "Disponibilitat\n" + "\n".join(found) + "\nToca per reservar.",
        )


if __name__ == "__main__":
    main()
