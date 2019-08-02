import os
import sqlite3


def get_db_connection():
    python_environment = os.environ.get('PYTHON_ENV', 'production')
    if python_environment == 'production':
        return sqlite3.connect('crawler.db')
    else:
        raise Exception('Unknown environment %s. Did you mean production?' % python_environment)
