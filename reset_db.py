from app.core.database import engine, Base, User
from app.core.security import hash_password
from sqlalchemy.orm import sessionmaker

def reset_and_seed():
    print("🗑️ Dropping all old tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("🏗️ Creating fresh tables from updated models...")
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    print("👤 Injecting new Admin account...")
    admin_user = User(
        username="admin",
        password=hash_password("admin123"),  # Securely hashed default password
        name="System Administrator",
        role="Admin",
        national_id="0000000000"
    )
    
    try:
        db.add(admin_user)
        db.commit()
        print("✅ Success! Database is fresh and ready.")
        print("--------------------------------------------------")
        print("You can now log in with:")
        print("Username: admin")
        print("Password: admin123")
        print("--------------------------------------------------")
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_and_seed()
