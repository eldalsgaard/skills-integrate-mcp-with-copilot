"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

DB_PATH = Path(__file__).parent / "activities.db"

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SEED_ACTIVITIES = [
    {
        "name": "Chess Club",
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    {
        "name": "Programming Class",
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    {
        "name": "Gym Class",
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    {
        "name": "Soccer Team",
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    {
        "name": "Basketball Team",
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    {
        "name": "Art Club",
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    {
        "name": "Drama Club",
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    {
        "name": "Math Club",
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    {
        "name": "Debate Team",
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
]


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                UNIQUE(activity_id, email),
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute("SELECT COUNT(*) FROM activities")
        existing_activities = cursor.fetchone()[0]

        if existing_activities == 0:
            for activity in SEED_ACTIVITIES:
                cursor.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        activity["name"],
                        activity["description"],
                        activity["schedule"],
                        activity["max_participants"],
                    ),
                )
                activity_id = cursor.lastrowid
                for email in activity["participants"]:
                    cursor.execute(
                        """
                        INSERT INTO activity_participants (activity_id, email)
                        VALUES (?, ?)
                        """,
                        (activity_id, email),
                    )
        connection.commit()


def load_activities() -> dict:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.name,
                a.description,
                a.schedule,
                a.max_participants,
                ap.email
            FROM activities a
            LEFT JOIN activity_participants ap ON ap.activity_id = a.id
            ORDER BY a.name, ap.email
            """
        )

        activities = {}
        for row in cursor.fetchall():
            activity_name = row["name"]
            if activity_name not in activities:
                activities[activity_name] = {
                    "description": row["description"],
                    "schedule": row["schedule"],
                    "max_participants": row["max_participants"],
                    "participants": [],
                }
            if row["email"]:
                activities[activity_name]["participants"].append(row["email"])
        return activities


def get_activity_id_by_name(connection: sqlite3.Connection, activity_name: str) -> int | None:
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM activities WHERE name = ?", (activity_name,))
    row = cursor.fetchone()
    if not row:
        return None
    return row["id"]


initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_connection() as connection:
        activity_id = get_activity_id_by_name(connection, activity_name)
        if not activity_id:
            raise HTTPException(status_code=404, detail="Activity not found")

        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM activity_participants WHERE activity_id = ? AND email = ?",
            (activity_id, email),
        )
        is_already_signed_up = cursor.fetchone()[0] > 0
        if is_already_signed_up:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        cursor.execute(
            "SELECT max_participants FROM activities WHERE id = ?",
            (activity_id,),
        )
        max_participants = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM activity_participants WHERE activity_id = ?",
            (activity_id,),
        )
        current_participants = cursor.fetchone()[0]
        if current_participants >= max_participants:
            raise HTTPException(status_code=400, detail="Activity is full")

        cursor.execute(
            "INSERT INTO activity_participants (activity_id, email) VALUES (?, ?)",
            (activity_id, email),
        )
        connection.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_connection() as connection:
        activity_id = get_activity_id_by_name(connection, activity_name)
        if not activity_id:
            raise HTTPException(status_code=404, detail="Activity not found")

        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM activity_participants WHERE activity_id = ? AND email = ?",
            (activity_id, email),
        )
        is_signed_up = cursor.fetchone()[0] > 0
        if not is_signed_up:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        cursor.execute(
            "DELETE FROM activity_participants WHERE activity_id = ? AND email = ?",
            (activity_id, email),
        )
        connection.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
