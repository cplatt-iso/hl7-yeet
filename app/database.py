# --- START OF FILE app/database.py ---
"""
This module primarily serves to provide a convenient way to get a db session.
The db instance itself is managed in extensions.py to keep all extensions together.
"""
from .extensions import db

# You could add helper functions here later if needed, e.g.,
# def get_db_session():
#     return db.session

# --- END OF FILE app/database.py ---