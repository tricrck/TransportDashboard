# inspect_tables.py
from app import create_app
from models import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    
    print("Permissions table columns:")
    if 'permissions' in inspector.get_table_names():
        columns = inspector.get_columns('permissions')
        for column in columns:
            print(f"  - {column['name']} ({column['type']})")
    else:
        print("Permissions table does not exist")
    
    print("\nAll tables:")
    for table in inspector.get_table_names():
        print(f"  - {table}")