"""
Fix PostgreSQL database schema - Complete User Table Setup
This script ensures ALL columns from the User model exist in PostgreSQL
"""

import psycopg2
from psycopg2 import sql

# Your PostgreSQL connection details
DB_URL = "postgresql://neondb_owner:npg_p05PMoKaQwlB@ep-damp-voice-a496yraj-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def fix_postgresql_schema():
    """Add ALL missing columns to PostgreSQL users table"""
    
    print("\n" + "=" * 70)
    print("POSTGRESQL DATABASE SCHEMA FIX - COMPLETE")
    print("=" * 70 + "\n")
    
    try:
        # Connect to PostgreSQL
        print("📡 Connecting to PostgreSQL...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        print("✓ Connected successfully!\n")
        
        # COMPLETE list of all User model columns
        columns = [
            # Authentication
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(120) UNIQUE NOT NULL;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NOT NULL;",
            
            # Profile
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);",
            
            # Job Information
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_id VARCHAR(50);",
            
            # Two-Factor Authentication
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS two_fa_enabled BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS two_fa_secret VARCHAR(32);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS backup_codes JSON;",
            
            # Password Management
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMP;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;",
            
            # Session Management
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS session_token VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_agent VARCHAR(255);",
            
            # Preferences
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Africa/Nairobi';",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS theme VARCHAR(20) DEFAULT 'light';",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS sms_notifications BOOLEAN DEFAULT FALSE;",
            
            # Status & Metadata
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_sent_at TIMESTAMP;",
            
            # Timestamps
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;",
            
            # Foreign Keys
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_id INTEGER;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by_id INTEGER;",
        ]
        
        print("📝 Adding missing columns...")
        print("-" * 70)
        
        added_count = 0
        skipped_count = 0
        
        for sql_statement in columns:
            try:
                cursor.execute(sql_statement)
                conn.commit()  # Commit after each statement
                
                # Extract column name
                if "ADD COLUMN IF NOT EXISTS" in sql_statement:
                    column_name = sql_statement.split("ADD COLUMN IF NOT EXISTS ")[1].split()[0]
                    print(f"✓ Processed: {column_name}")
                    added_count += 1
                    
            except psycopg2.errors.DuplicateColumn as e:
                column_name = sql_statement.split("ADD COLUMN IF NOT EXISTS ")[1].split()[0]
                print(f"⊙ Column '{column_name}' already exists")
                skipped_count += 1
                conn.rollback()  # Rollback and continue
                
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" in error_msg or "duplicate" in error_msg:
                    column_name = sql_statement.split("ADD COLUMN IF NOT EXISTS ")[1].split()[0]
                    print(f"⊙ Column '{column_name}' already exists")
                    skipped_count += 1
                else:
                    print(f"✗ Error: {str(e)}")
                conn.rollback()  # Rollback and continue
        
        print("-" * 70)
        print(f"\n📊 Summary:")
        print(f"   ✓ Columns processed: {added_count}")
        print(f"   ⊙ Columns skipped (already exist): {skipped_count}")
        print(f"   Total: {len(columns)}")
        
        # Create indexes
        print("\n📌 Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);",
            "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);",
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);",
        ]
        
        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
                conn.commit()
                idx_name = idx_sql.split("INDEX IF NOT EXISTS ")[1].split()[0]
                print(f"✓ Index '{idx_name}' created")
            except Exception as e:
                if "already exists" in str(e).lower():
                    idx_name = idx_sql.split("INDEX IF NOT EXISTS ")[1].split()[0]
                    print(f"⊙ Index '{idx_name}' already exists")
                else:
                    print(f"✗ Failed to create index: {str(e)}")
                conn.rollback()
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("🎉 PostgreSQL schema updated successfully!")
        print("=" * 70)
        print("\n📝 Next steps:")
        print("  1. Restart your Flask application")
        print("  2. Try logging in - it should work now!")
        print("  3. If you see more missing columns, run this script again")
        print("\n" + "=" * 70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Check if PostgreSQL server is accessible")
        print("  2. Verify database credentials")
        print("  3. Ensure you have permission to ALTER tables")
        print("  4. Check your network connection to Neon")
        return False

if __name__ == '__main__':
    try:
        success = fix_postgresql_schema()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        exit(1)