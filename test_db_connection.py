#!/usr/bin/env python3
"""Test database connection to verify which database is being used"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("DATABASE CONNECTION TEST")
print("=" * 60)

# Check what's in the environment
database_url = os.getenv('DATABASE_URL')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')

print(f"\nDATABASE_URL: {database_url[:50] if database_url else 'NOT SET'}...")
print(f"DB_HOST: {db_host}")
print(f"DB_NAME: {db_name}")

if database_url:
    if 'supabase' in database_url:
        print("\n✅ Will connect to: SUPABASE")
    elif 'localhost' in database_url:
        print("\n⚠️  Will connect to: LOCAL PostgreSQL")
    else:
        print("\n🔍 Will connect to: UNKNOWN")
else:
    print("\n⚠️  DATABASE_URL not set - will use individual DB_* variables")
    print(f"   → Connecting to: {db_host}:{os.getenv('DB_PORT')}/{db_name}")

print("\n" + "=" * 60)

# Now test actual connection
print("\nTesting actual connection...")
from database import Database

db = Database()
print(f"\nConnection params type: {type(db.conn_params)}")
if isinstance(db.conn_params, str):
    print(f"Connection string: {db.conn_params[:50]}...")
else:
    print(f"Connection dict: {db.conn_params}")

try:
    db.connect()
    db.cursor.execute("SELECT current_database(), current_user, version();")
    result = db.cursor.fetchone()
    print(f"\n✅ Connected successfully!")
    print(f"   Database: {result['current_database']}")
    print(f"   User: {result['current_user']}")
    print(f"   Version: {result['version'][:60]}...")

    # Check if we're on Supabase
    if 'supabase' in result['version'].lower() or 'supabase' in str(result):
        print("\n🎉 Connected to SUPABASE!")
    else:
        print("\n⚠️  Connected to LOCAL PostgreSQL")

    db.close()
except Exception as e:
    print(f"\n❌ Connection failed: {e}")

print("=" * 60)
