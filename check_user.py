#!/usr/bin/env python3
"""Script to check user admin status in the database."""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Build database URL from environment variables
POSTGRES_USER = os.getenv('POSTGRES_USER', 'yeeter_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'yeeter_pw')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'hl7_yeeter_db')
POSTGRES_HOST = 'localhost'
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5434')

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

print(f"Connecting to database...")
print(f"Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
print(f"Database: {POSTGRES_DB}")
print(f"User: {POSTGRES_USER}")
print()

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if the user exists
        email = 'chris.platt@gmail.com'
        result = conn.execute(
            text("SELECT id, username, email, is_admin, created_at, google_id FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()
        
        if user:
            print(f"✓ User found!")
            print(f"  ID: {user[0]}")
            print(f"  Username: {user[1]}")
            print(f"  Email: {user[2]}")
            print(f"  Is Admin: {user[3]}")
            print(f"  Created At: {user[4]}")
            print(f"  Google ID: {user[5]}")
            print()
            
            if not user[3]:
                print("❌ User is NOT an admin")
                print()
                print("To make this user an admin, run:")
                print(f"  python fix_admin.py")
            else:
                print("✓ User IS an admin")
        else:
            print(f"❌ User with email '{email}' not found in database")
            print()
            print("Listing all users:")
            result = conn.execute(text("SELECT id, username, email, is_admin FROM users ORDER BY id"))
            users = result.fetchall()
            if users:
                for u in users:
                    admin_marker = "👑" if u[3] else "  "
                    print(f"  {admin_marker} ID: {u[0]}, Username: {u[1]}, Email: {u[2]}, Admin: {u[3]}")
            else:
                print("  No users found in database")
                
except Exception as e:
    print(f"❌ Error connecting to database: {e}")
    print()
    print("Make sure:")
    print("  1. PostgreSQL is running (check docker-compose)")
    print("  2. Port 5434 is accessible")
    print("  3. Database credentials in .env are correct")
