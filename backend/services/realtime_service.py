import random
from datetime import datetime, timezone


EVENTS = [
    {"kind": "weather", "title": "Pluie mobile", "body": "Une zone de pluie avance sur les nationales.", "severity": "info"},
    {"kind": "bonus", "title": "Covoitureurs", "body": "Des passagers cherchent une Twingo souriante.", "severity": "success"},
    {"kind": "malus", "title": "Radar", "body": "Radar annonce pres d'une autoroute rapide.", "severity": "warning"},
    {"kind": "garage", "title": "Garage ouvert", "body": "Un garage propose un check-up rapide.", "severity": "info"},
    {"kind": "weather", "title": "Brouillard", "body": "Visibilite reduite autour des peages.", "severity": "warning"},
]


def next_realtime_event():
    event = random.choice(EVENTS).copy()
    event["at"] = datetime.now(timezone.utc).isoformat()
    return event
