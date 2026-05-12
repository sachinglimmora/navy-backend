"""
GLIMMORA AEGIS — Database Seed Script
Run with: python seeds/seed_data.py

Seeds 7 users (matching frontend mock data), 5 scenarios, and 3 doctrine documents.
Idempotent: re-running skips existing records by service_number / title.
"""

import os
import sys
import uuid
from datetime import UTC, datetime

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.doctrine import DoctrineDocument
from app.models.scenario import Scenario
from app.models.user import User
from app.services.auth_service import hash_password


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# User seed definitions — 7 roles matching the frontend mock users exactly
# ---------------------------------------------------------------------------
USERS = [
    {
        "service_number": "IN-2024-001",
        "name": "LT Jayesh Kumar",
        "rank": "LT",
        "unit": "INS Vikrant",
        "role": "trainee",
        "password": "aegis123",
        "classification_clearance": "RESTRICTED",
    },
    {
        "service_number": "IN-2019-042",
        "name": "CDR Arjun Sharma",
        "rank": "CDR",
        "unit": "INS Dronacharya",
        "role": "instructor",
        "password": "aegis123",
        "classification_clearance": "SECRET",
    },
    {
        "service_number": "IN-2015-018",
        "name": "CAPT Priya Menon",
        "rank": "CAPT",
        "unit": "Fleet Training Centre",
        "role": "evaluator",
        "password": "aegis123",
        "classification_clearance": "SECRET",
    },
    {
        "service_number": "IN-2016-031",
        "name": "CDR Rakesh Iyer",
        "rank": "CDR",
        "unit": "Naval Doctrine Cell",
        "role": "doctrine",
        "password": "aegis123",
        "classification_clearance": "TOP SECRET",
    },
    {
        "service_number": "IN-2010-007",
        "name": "RADM Vikram Bhatia",
        "rank": "RADM",
        "unit": "Fleet Training Command",
        "role": "fleet",
        "password": "aegis123",
        "classification_clearance": "TOP SECRET",
    },
    {
        "service_number": "IN-2008-003",
        "name": "CMDE Sanjay Rao",
        "rank": "CMDE",
        "unit": "Systems Authority",
        "role": "admin",
        "password": "aegis123",
        "classification_clearance": "TOP SECRET",
    },
    {
        "service_number": "IN-2017-055",
        "name": "CDR Ananya Rao",
        "rank": "CDR",
        "unit": "Sustainment Cell",
        "role": "maintainer",
        "password": "aegis123",
        "classification_clearance": "SECRET",
    },
]


# ---------------------------------------------------------------------------
# Scenario seed definitions — one per domain
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "title": "Bridge Watch — Restricted Waters Navigation",
        "domain": "bridge",
        "difficulty": "intermediate",
        "doctrine_version": "1.0",
        "estimated_duration_minutes": 90,
        "tags": ["navigation", "bridge", "colregs", "restricted-waters"],
        "definition": {
            "objectives": [
                "Navigate through simulated restricted channel safely",
                "Apply COLREGS Rule 9 — Narrow Channels",
                "Coordinate with CIC for traffic picture",
            ],
            "initial_conditions": {
                "weather": "Visibility 3nm, Sea State 3",
                "traffic": "3 merchant vessels in channel",
                "time": "Dusk — civil twilight",
                "own_ship": "INS Vikrant, speed 8 knots, heading 045",
            },
            "events": [
                {"t_plus_mins": 5, "event": "Merchant vessel alters course unexpectedly"},
                {"t_plus_mins": 15, "event": "Engine room reports reduced propulsion"},
                {"t_plus_mins": 25, "event": "VHF channel 16 distress call nearby"},
            ],
            "success_criteria": {
                "no_collision": True,
                "speed_compliance": True,
                "correct_signals_used": True,
                "timely_reporting": True,
            },
            "evaluation_rubric": {
                "situational_awareness": 0.30,
                "rules_application": 0.40,
                "communications": 0.20,
                "decision_speed": 0.10,
            },
        },
    },
    {
        "title": "CIC Operations — Anti-Air Threat Prosecution",
        "domain": "cic",
        "difficulty": "advanced",
        "doctrine_version": "1.0",
        "estimated_duration_minutes": 120,
        "tags": ["cic", "anti-air", "threat-prosecution", "radar"],
        "definition": {
            "objectives": [
                "Classify and track inbound air contacts",
                "Coordinate with OOW for manoeuvring",
                "Execute weapons engagement per ROE",
            ],
            "initial_conditions": {
                "weather": "Clear, Sea State 2",
                "contacts": [
                    {"id": "TGT-01", "type": "unknown-air", "bearing": "270", "range_nm": 40},
                    {"id": "TGT-02", "type": "friendly-helo", "bearing": "090", "range_nm": 15},
                ],
                "own_ship": "INS Vishakhapatnam, AA Defence State 2",
            },
            "events": [
                {"t_plus_mins": 8, "event": "TGT-01 IFF returns hostile"},
                {"t_plus_mins": 12, "event": "TGT-01 descends to sea-skimmer altitude"},
                {"t_plus_mins": 18, "event": "Jamming on primary radar"},
            ],
            "success_criteria": {
                "correct_id_within_5min": True,
                "engagement_authorisation_correct": True,
                "blue_on_blue_avoided": True,
            },
            "evaluation_rubric": {
                "contact_management": 0.35,
                "threat_assessment": 0.35,
                "weapons_coordination": 0.20,
                "communications": 0.10,
            },
        },
    },
    {
        "title": "Engineering — Propulsion Casualty Control",
        "domain": "engineering",
        "difficulty": "advanced",
        "doctrine_version": "1.0",
        "estimated_duration_minutes": 75,
        "tags": ["engineering", "propulsion", "casualty-control", "engine-room"],
        "definition": {
            "objectives": [
                "Respond to sudden propulsion failure at sea",
                "Implement casualty control procedures",
                "Restore propulsion within 30 minutes",
                "Maintain safe electrical load",
            ],
            "initial_conditions": {
                "weather": "Sea State 4, 25 knot wind",
                "state": "Ship underway at 15 knots, open ocean",
                "crew": "Normal sea watch",
            },
            "events": [
                {"t_plus_mins": 0, "event": "STBD GT trips — loss of starboard propulsion"},
                {"t_plus_mins": 2, "event": "Electrical bus load alarm"},
                {"t_plus_mins": 10, "event": "Lube oil pressure low on port GT"},
                {"t_plus_mins": 20, "event": "Flooding alarm in engine room bilge"},
            ],
            "success_criteria": {
                "propulsion_restored_30min": True,
                "no_secondary_casualties": True,
                "correct_reporting": True,
            },
            "evaluation_rubric": {
                "procedure_compliance": 0.40,
                "speed_of_response": 0.25,
                "communication": 0.20,
                "leadership": 0.15,
            },
        },
    },
    {
        "title": "Damage Control — Fire and Flooding Scenario",
        "domain": "damage_control",
        "difficulty": "extreme",
        "doctrine_version": "1.0",
        "estimated_duration_minutes": 60,
        "tags": ["damage-control", "fire", "flooding", "survivability"],
        "definition": {
            "objectives": [
                "Control simultaneous fire and flooding",
                "Maintain ship stability",
                "Conduct correct personnel accounting",
                "Prevent loss of watertight integrity",
            ],
            "initial_conditions": {
                "weather": "Night, Sea State 3",
                "state": "Ship in harbour, reduced watch",
                "threat": "Uncontrolled fire in 2-deck stores + flooding in forward bilge",
            },
            "events": [
                {"t_plus_mins": 0, "event": "Fire alarm activates — 2 Deck Fwd stores"},
                {"t_plus_mins": 3, "event": "Flooding detected — Frame 15 bilge"},
                {"t_plus_mins": 8, "event": "Fire spreads to adjacent compartment"},
                {"t_plus_mins": 15, "event": "Power failure to forward section"},
                {"t_plus_mins": 25, "event": "Stability warning — 8 degree list"},
            ],
            "success_criteria": {
                "fire_contained_20min": True,
                "flooding_stopped_15min": True,
                "no_personnel_casualties": True,
                "list_corrected": True,
            },
            "evaluation_rubric": {
                "prioritisation": 0.30,
                "team_coordination": 0.30,
                "technical_execution": 0.25,
                "reporting": 0.15,
            },
        },
    },
    {
        "title": "Small Boats — VBSS Boarding Operation",
        "domain": "small_boats",
        "difficulty": "advanced",
        "doctrine_version": "1.0",
        "estimated_duration_minutes": 90,
        "tags": ["small-boats", "vbss", "boarding", "maritime-security"],
        "definition": {
            "objectives": [
                "Execute Visit Board Search and Seizure (VBSS) procedure",
                "Maintain radio discipline throughout",
                "Complete documentation and evidence preservation",
            ],
            "initial_conditions": {
                "weather": "Day, Sea State 2, 10 knot wind",
                "target": "Suspected drug smuggling dhow",
                "own_forces": "2 x RIBS, 8-person boarding team, armed",
            },
            "events": [
                {"t_plus_mins": 5, "event": "Target vessel attempts evasion"},
                {"t_plus_mins": 12, "event": "Boarding team aboard — armed crew member identified"},
                {"t_plus_mins": 20, "event": "Contraband found — evidence handling required"},
                {"t_plus_mins": 35, "event": "Weather deteriorates — RHIB recovery required"},
            ],
            "success_criteria": {
                "no_blue_casualties": True,
                "correct_escalation_of_force": True,
                "evidence_preserved": True,
                "comms_maintained": True,
            },
            "evaluation_rubric": {
                "tactical_execution": 0.35,
                "rules_of_engagement": 0.30,
                "evidence_handling": 0.20,
                "communications": 0.15,
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Doctrine document seed data
# ---------------------------------------------------------------------------
DOCTRINE_DOCS = [
    {
        "title": "Navigation Safety Manual",
        "domain": "bridge",
        "version": "1.0",
        "content_text": (
            "Navigation Safety Manual — Indian Navy Edition 1.0\n\n"
            "1. COLREGS Application\nAll officers of the watch shall apply the International "
            "Regulations for Preventing Collisions at Sea (COLREGS) without exception. "
            "Rule 8 — Action to Avoid Collision — requires early and substantial action. "
            "Rule 9 — Narrow Channels — vessels shall keep to the starboard side of the "
            "fairway or channel as near as is safe and practicable.\n\n"
            "2. Bridge Team Management\nThe OOW shall maintain an effective lookout by sight "
            "and hearing and by all available means. The navigator shall cross-check all "
            "electronic position fixes with visual bearings where possible.\n\n"
            "3. Speed in Restricted Visibility\nIn or near an area of restricted visibility, "
            "a vessel shall proceed at a safe speed adapted to the prevailing circumstances "
            "and conditions. All engines shall be ready for immediate manoeuvre.\n\n"
            "4. Anchoring Procedures\nPrior to anchoring, OOW shall verify holding ground, "
            "scope requirement, and swing circle clearance. Anchor party to be briefed and "
            "stationed 30 minutes prior."
        ),
    },
    {
        "title": "Combat Information Centre Operations Manual",
        "domain": "cic",
        "version": "1.0",
        "content_text": (
            "CIC Operations Manual — Indian Navy Edition 1.0\n\n"
            "1. Track Management\nAll air and surface contacts shall be assigned a track "
            "number within 60 seconds of detection. Track quality ratings (TQ1–TQ5) shall be "
            "maintained and broadcast to all stations.\n\n"
            "2. IFF Procedures\nInterrogation of all contacts shall occur on initial detection. "
            "Squawk mode 3/A responses shall be verified against flight plans. Hostile "
            "declaration requires BOTH no valid IFF AND hostile intent demonstrated.\n\n"
            "3. Weapons Engagement Authority\nEngagement of air threats requires: "
            "(a) Hostile identification, (b) Weapons Free authority from CO, "
            "(c) Safety bearing verification, (d) Blue force deconfliction.\n\n"
            "4. Electronic Warfare\nOn detection of jamming or spoofing, CIC shall "
            "immediately switch to alternate sensor suite, notify CO, and increase "
            "lookout watch. All sensor degradation shall be logged."
        ),
    },
    {
        "title": "Damage Control Manual",
        "domain": "damage_control",
        "version": "1.0",
        "content_text": (
            "Damage Control Manual — Indian Navy Edition 1.0\n\n"
            "1. DCRO Responsibilities\nThe Damage Control Repair Officer is responsible for "
            "the execution of all DC drills and operational response. DCRO shall maintain a "
            "current stability booklet and damage control plan.\n\n"
            "2. Fire Classification\nFires are classified: Class A (Solid combustibles), "
            "Class B (Flammable liquids), Class C (Electrical), Class D (Metal). "
            "Correct extinguishant selection is critical — water on Class C or D fires "
            "is prohibited.\n\n"
            "3. Flooding Response\nOn discovery of flooding: (a) Sound alarm, "
            "(b) Identify source and attempt isolation, (c) Pump out if safe, "
            "(d) Shore up structure with timber shores, (e) Report to DCO.\n\n"
            "4. Stability Management\nIf list exceeds 5 degrees, DCRO shall convene "
            "stability meeting immediately. Damage stability calculations shall be "
            "performed before transferring ballast. Minimum GM of 0.15m to be maintained.\n\n"
            "5. Abandonment\nAbandonment shall only be ordered by the Commanding Officer. "
            "Sequence: Personal survival equipment, emergency radio, liferafts, "
            "man overboard drill, distress signal."
        ),
    },
]


def seed(db):
    print("Seeding GLIMMORA AEGIS database...")

    # --- Admin user as creator for scenarios/docs ---
    # Find or create admin first (needed as FK for scenarios)
    admin_user = None

    # Create users
    created_users: dict[str, User] = {}
    for u_data in USERS:
        existing = db.query(User).filter(User.service_number == u_data["service_number"]).first()
        if existing:
            print(f"  [SKIP] User exists: {u_data['service_number']} — {u_data['name']}")
            created_users[u_data["service_number"]] = existing
        else:
            user = User(
                id=uuid.uuid4(),
                service_number=u_data["service_number"],
                name=u_data["name"],
                rank=u_data["rank"],
                unit=u_data["unit"],
                role=u_data["role"],
                password_hash=hash_password(u_data["password"]),
                classification_clearance=u_data["classification_clearance"],
                is_active=True,
                created_at=_now(),
                updated_at=_now(),
            )
            db.add(user)
            db.flush()
            created_users[u_data["service_number"]] = user
            print(
                f"  [OK]   Created user: {u_data['service_number']} — {u_data['name']} ({u_data['role']})"
            )

    db.commit()

    # Identify admin and instructor for FK usage
    admin_user = created_users.get("IN-2008-003")
    created_users.get("IN-2019-042")
    creator_id = admin_user.id if admin_user else list(created_users.values())[0].id

    # Create scenarios
    for s_data in SCENARIOS:
        existing = db.query(Scenario).filter(Scenario.title == s_data["title"]).first()
        if existing:
            print(f"  [SKIP] Scenario exists: {s_data['title'][:60]}")
        else:
            scenario = Scenario(
                id=uuid.uuid4(),
                title=s_data["title"],
                domain=s_data["domain"],
                difficulty=s_data["difficulty"],
                doctrine_version=s_data["doctrine_version"],
                definition=s_data["definition"],
                created_by=creator_id,
                estimated_duration_minutes=s_data["estimated_duration_minutes"],
                tags=s_data["tags"],
                is_archived=False,
                created_at=_now(),
                updated_at=_now(),
            )
            db.add(scenario)
            print(f"  [OK]   Created scenario: {s_data['title'][:60]} ({s_data['domain']})")

    db.commit()

    # Create doctrine documents
    for d_data in DOCTRINE_DOCS:
        existing = (
            db.query(DoctrineDocument).filter(DoctrineDocument.title == d_data["title"]).first()
        )
        if existing:
            print(f"  [SKIP] Doctrine doc exists: {d_data['title']}")
        else:
            import hashlib

            content_hash = hashlib.sha256(d_data["content_text"].encode()).hexdigest()
            doc = DoctrineDocument(
                id=uuid.uuid4(),
                title=d_data["title"],
                domain=d_data["domain"],
                version=d_data["version"],
                content_hash=content_hash,
                content_text=d_data["content_text"],
                is_active=True,
                approved_by=creator_id,
                created_at=_now(),
                updated_at=_now(),
            )
            db.add(doc)
            print(f"  [OK]   Created doctrine doc: {d_data['title']} (v{d_data['version']})")

    db.commit()
    print("\nSeed complete.")
    print(f"  Users seeded:          {len(USERS)}")
    print(f"  Scenarios seeded:      {len(SCENARIOS)}")
    print(f"  Doctrine docs seeded:  {len(DOCTRINE_DOCS)}")
    print("\nDefault credentials for all users: password = aegis123")
    print("\nUser summary:")
    for u in USERS:
        print(f"  {u['service_number']:20s}  {u['rank']:6s}  {u['role']:12s}  {u['name']}")


if __name__ == "__main__":
    # Create tables if they don't exist (useful for fresh dev environments)
    from app.database import create_all_tables

    print("Ensuring database tables exist...")
    create_all_tables()

    db = SessionLocal()
    try:
        seed(db)
    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] Seed failed: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()
