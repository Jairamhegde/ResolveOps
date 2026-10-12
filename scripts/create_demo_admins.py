"""
Create the dashboard demo super admin, or reset its password if it already exists.

Run it from the project root:
    python -m scripts.create_demo_admins
"""
from backend.database import SessionLocal
from backend.models import Admin
from backendapi.routes.auth_routes import hash_password

DEMO_EMAIL = "super@demo.com"
DEMO_PASSWORD = "demo-super-123"

db = SessionLocal()
admin = db.query(Admin).filter(Admin.email == DEMO_EMAIL).first()
if admin is None:
    admin = Admin(email=DEMO_EMAIL)
admin.role = "super_admin"
admin.password_hash = hash_password(DEMO_PASSWORD)
db.add(admin)
db.commit()
db.close()
print(f"Demo super admin ready: {DEMO_EMAIL}")
