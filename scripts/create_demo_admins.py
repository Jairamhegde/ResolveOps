"""
Create the dashboard demo accounts, or reset their passwords if they already exist:
an admin who only sees network tickets, a super admin who sees everything,
and a user who only sees the tickets they submitted.

The user is a real Slack user who has already raised tickets, so they must be in the
users table first (they are added the first time they run /helpdesk).

Run it from the project root:
    python -m scripts.create_demo_admins
"""
from backend.database import SessionLocal
from backend.models import Admin, User
from backendapi.routes.auth_routes import hash_password

DEMO_ADMINS = [
    {"email": "network@demo.com", "password": "demo-network-123", "role": "network"},
    {"email": "super@demo.com", "password": "demo-super-123", "role": "super_admin"},
]

DEMO_USER = {"email": "jairamkansur@gmail.com", "password": "demo-user-123"}

db = SessionLocal()

for demo in DEMO_ADMINS:
    admin = db.query(Admin).filter(Admin.email == demo["email"]).first()
    if admin is None:
        admin = Admin(email=demo["email"])
    admin.role = demo["role"]
    admin.password_hash = hash_password(demo["password"])
    db.add(admin)
    print(f"Demo {demo['role']} admin ready: {demo['email']}")

user = db.query(User).filter(User.email == DEMO_USER["email"]).first()
if user is None:
    print(f"No user with the email {DEMO_USER['email']}. Raise a ticket with /helpdesk in Slack first, then run this again.")
else:
    user.password_hash = hash_password(DEMO_USER["password"])
    db.add(user)
    print(f"Demo user ready: {DEMO_USER['email']}")

db.commit()
db.close()
