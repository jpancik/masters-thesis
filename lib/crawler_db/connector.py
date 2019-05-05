import os
import sqlite3

import psycopg2


def get_db_connection():
    python_environment = os.environ.get('PYTHON_ENV', 'local')
    if python_environment == 'local':
        return psycopg2.connect("dbname=crawlerdb user=jurajpancik")
    elif python_environment == 'production':
        db_password_filepath = 'files/db_password'
        if not os.path.exists(db_password_filepath):
            raise Exception('Create files/db_password that contains database password on first line without a new line.')

        with open('files/db_password', 'r') as db_password_file:
            db_password = db_password_file.read().strip()

        return psycopg2.connect("host=db.fi.muni.cz dbname=pgdb user=xpancik2 password=%s" % db_password)
    else:
        raise Exception('Unknown environment %s. Did you mean local or production?' % python_environment)
