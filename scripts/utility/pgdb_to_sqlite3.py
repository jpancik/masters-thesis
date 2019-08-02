import sqlite3

from lib.crawler_db import connector

pgdb_conn = connector.get_db_connection()
pgdb_cur = pgdb_conn.cursor()

# Set up sqlite3 db.
sqlite3_conn = sqlite3.connect('pgdb_dump.db')
sqlite3_conn.execute(
'CREATE TABLE article_metadata ('
  'id INTEGER PRIMARY KEY,'
  'website_domain TEXT NOT NULL,'
  'url TEXT NOT NULL,'
  'title TEXT,'
  'publication_date DATETIME,'
  'created_at DATETIME DEFAULT CURRENT_TIMESTAMP'
');')
sqlite3_conn.execute(
'CREATE TABLE article_metadata_gathering_summary ('
  'id INTEGER PRIMARY KEY,'
  'website_domain TEXT NOT NULL,'
  'total_articles_count INTEGER NOT NULL,'
  'new_articles_count INTEGER NOT NULL,'
  'created_at DATETIME DEFAULT CURRENT_TIMESTAMP'
');')
sqlite3_conn.execute(
'CREATE TABLE article_raw_html ('
  'id INTEGER PRIMARY KEY,'
  'article_metadata_id INTEGER NOT NULL,'
  'filename TEXT NOT NULL,'
  'created_at DATETIME DEFAULT CURRENT_TIMESTAMP'
');')
sqlite3_conn.execute(
'CREATE TABLE article_processing_summary ('
  'id INTEGER PRIMARY KEY,'
  'website_domain TEXT NOT NULL,'
  'empty_title_count INTEGER NOT NULL,'
  'empty_author_count INTEGER NOT NULL,'
  'empty_publication_date_count INTEGER NOT NULL,'
  'empty_perex_count INTEGER NOT NULL,'
  'empty_keywords_count INTEGER NOT NULL,'
  'empty_article_content_count INTEGER NOT NULL,'
  'total_articles_processed_count INTEGER NOT NULL,'
  'start_article_id INTEGER NOT NULL,'
  'end_article_id INTEGER NOT NULL,'
  'created_at DATETIME DEFAULT CURRENT_TIMESTAMP'
');')
sqlite3_conn.execute(
'CREATE TABLE article_processed_data ('
  'id INTEGER PRIMARY KEY,'
  'website_domain TEXT NOT NULL,'
  'article_metadata_id INTEGER,'
  'article_processing_summary_id INTEGER,'
  'filename TEXT NOT NULL,'
  'created_at DATETIME DEFAULT CURRENT_TIMESTAMP'
');')

# Transfer data table by table.
# Table: article_metadata.
batch_index = 0
query = 'SELECT * FROM article_metadata OFFSET {offset} LIMIT 1000;'

pgdb_cur.execute(query.format(offset=batch_index * 1000))
data = pgdb_cur.fetchall()
while data:
    for id, website_domain, url, title, publication_date, created_at in data:
        sqlite3_conn.execute(
            'INSERT INTO article_metadata (id, website_domain, url, title, publication_date, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (id, website_domain, url, title, publication_date, created_at))

    print('Finished article_metadata %s' % (batch_index * 1000))
    batch_index += 1
    pgdb_cur.execute(query.format(offset=batch_index * 1000))
    data = pgdb_cur.fetchall()
sqlite3_conn.commit()

# Table: article_metadata_gathering_summary.
batch_index = 0
query = 'SELECT * FROM article_metadata_gathering_summary OFFSET {offset} LIMIT 1000;'

pgdb_cur.execute(query.format(offset=batch_index * 1000))
data = pgdb_cur.fetchall()
while data:
    for id, website_domain, total_articles_count, new_articles_count, created_at in data:
        sqlite3_conn.execute(
            'INSERT INTO article_metadata_gathering_summary (id, website_domain, total_articles_count, new_articles_count, created_at) VALUES (?, ?, ?, ?, ?)',
            (id, website_domain, total_articles_count, new_articles_count, created_at))

    print('Finished article_metadata_gathering_summary %s' % (batch_index * 1000))
    batch_index += 1
    pgdb_cur.execute(query.format(offset=batch_index * 1000))
    data = pgdb_cur.fetchall()
sqlite3_conn.commit()

# Table: article_raw_html.
batch_index = 0
query = 'SELECT * FROM article_raw_html OFFSET {offset} LIMIT 1000;'

pgdb_cur.execute(query.format(offset=batch_index * 1000))
data = pgdb_cur.fetchall()
while data:
    for id, article_metadata_id, filename, created_at in data:
        sqlite3_conn.execute(
            'INSERT INTO article_raw_html (id, article_metadata_id, filename, created_at) VALUES (?, ?, ?, ?)',
            (id, article_metadata_id, filename, created_at))

    print('Finished article_raw_html %s' % (batch_index * 1000))
    batch_index += 1
    pgdb_cur.execute(query.format(offset=batch_index * 1000))
    data = pgdb_cur.fetchall()
sqlite3_conn.commit()

# Table: article_processing_summary.
batch_index = 0
query = 'SELECT * FROM article_processing_summary OFFSET {offset} LIMIT 1000;'

pgdb_cur.execute(query.format(offset=batch_index * 1000))
data = pgdb_cur.fetchall()
while data:
    for (id, website_domain,
         empty_title_count, empty_author_count, empty_publication_date_count,
         empty_perex_count, empty_keywords_count, empty_article_content_count,
         total_articles_processed_count, start_article_id, end_article_id, created_at) in data:
        sqlite3_conn.execute(
            'INSERT INTO article_processing_summary (id, website_domain, empty_title_count, empty_author_count, '
            'empty_publication_date_count, empty_perex_count, empty_keywords_count, empty_article_content_count, '
            'total_articles_processed_count, start_article_id, end_article_id, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (id, website_domain,
             empty_title_count, empty_author_count, empty_publication_date_count,
             empty_perex_count, empty_keywords_count, empty_article_content_count,
             total_articles_processed_count, start_article_id, end_article_id, created_at))

    print('Finished article_processing_summary %s' % (batch_index * 1000))
    batch_index += 1
    pgdb_cur.execute(query.format(offset=batch_index * 1000))
    data = pgdb_cur.fetchall()
sqlite3_conn.commit()

# Table: article_processed_data.
batch_index = 0
query = 'SELECT * FROM article_processed_data OFFSET {offset} LIMIT 1000;'

pgdb_cur.execute(query.format(offset=batch_index * 1000))
data = pgdb_cur.fetchall()
while data:
    for id, website_domain, article_metadata_id, article_processing_summary_id, filename, created_at in data:
        sqlite3_conn.execute(
            'INSERT INTO article_processed_data (id, website_domain, article_metadata_id, article_processing_summary_id, filename, created_at) VALUES (?, ?, ?, ?, ? ,?)',
            (id, website_domain, article_metadata_id, article_processing_summary_id, filename, created_at))

    print('Finished article_processed_data %s' % (batch_index * 1000))
    batch_index += 1
    pgdb_cur.execute(query.format(offset=batch_index * 1000))
    data = pgdb_cur.fetchall()
sqlite3_conn.commit()

sqlite3_conn.close()

pgdb_cur.close()
pgdb_conn.close()