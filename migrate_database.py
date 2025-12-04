#!/usr/bin/env python3
"""
Database Migration Script
Backs up old database and creates new simplified schema
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path


def migrate_database():
    """Migrate to simplified database schema"""

    db_file = Path('reconraven.db')

    print('=' * 70)
    print('ReconRaven Database Migration')
    print('=' * 70)
    print()

    # Check if database exists
    if db_file.exists():
        # Backup old database
        backup_file = f'reconraven_backup_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.db'
        print(f'📦 Backing up existing database to: {backup_file}')
        shutil.copy2(db_file, backup_file)
        print('✅ Backup created successfully')
        print()

        # Remove old database
        print(f'🗑️  Removing old database: {db_file}')
        db_file.unlink()
        print('✅ Old database removed')
        print()
    else:
        print('ℹ️  No existing database found')
        print()

    # Create new database with simplified schema
    print('🔨 Creating new simplified database schema...')
    from database import get_db

    db = get_db()
    print('✅ New database created with flat schema')
    print()

    # Show schema info
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print('📊 New database tables:')
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'   - {table}: {count} rows')
    print()

    print('=' * 70)
    print('✅ Migration Complete!')
    print('=' * 70)
    print()
    print('The database has been rebuilt with a simplified schema.')
    print('All old data has been backed up.')
    print('You can now start scanning with a clean database.')
    print()


if __name__ == '__main__':
    migrate_database()
