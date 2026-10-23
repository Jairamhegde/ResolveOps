"""
Create the dashboard demo accounts, or reset their passwords if they already exist:
a super admin who sees everything, a network admin who only sees network tickets,
and an employee who only sees the tickets they submitted.

Run it from the project root:
    python -m scripts.create_demo_admins
"""
from backend.database import SessionLocal
from backend.models import Admin, User
from backendapi.routes.auth_routes import hash_password

DEMO_ADMINS = [
    {"email": "super@demo.com", "password": "demo-super-123", "role": "super_admin"},
    {"email": "network@demo.com", "password": "demo-network-123", "role": "network"},
]

DEMO_EMPLOYEE = {"slack_id": "UDEMOEMPLOYEE", "name": "Demo Employee", "email": "employee@demo.com", "password": "demo-employee-123"}

db = SessionLocal()

for demo in DEMO_ADMINS:
    admin = db.query(Admin).filter(Admin.email == demo["email"]).first()
    if admin is None:
        admin = Admin(email=demo["email"])
    admin.role = demo["role"]
    admin.password_hash = hash_password(demo["password"])
    db.add(admin)
    print(f"Demo {demo['role']} admin ready: {demo['email']}")

employee = db.query(User).filter(User.email == DEMO_EMPLOYEE["email"]).first()
if employee is None:
    employee = User(slack_id=DEMO_EMPLOYEE["slack_id"], name=DEMO_EMPLOYEE["name"], email=DEMO_EMPLOYEE["email"])
employee.password_hash = hash_password(DEMO_EMPLOYEE["password"])
db.add(employee)
print(f"Demo employee ready: {DEMO_EMPLOYEE['email']}")

db.commit()
db.close()
