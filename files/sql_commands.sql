-- Init tables.
CREATE TABLE article_metadata (
  id SERIAL PRIMARY KEY,
  website_domain VARCHAR(100) NOT NULL,
  url VARCHAR(2083) NOT NULL,
  title TEXT,
  publication_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE article_metadata_gathering_summary (
  id SERIAL PRIMARY KEY,
  website_domain VARCHAR(100) NOT NULL,
  total_articles_count INT NOT NULL,
  new_articles_count INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE article_raw_html (
  id SERIAL PRIMARY KEY,
  article_metadata_id INT NOT NULL,
  filename TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE article_processing_summary (
  id SERIAL PRIMARY KEY,
  website_domain VARCHAR(100) NOT NULL,
  empty_title_count INT NOT NULL,
  empty_author_count INT NOT NULL,
  empty_publication_date_count INT NOT NULL,
  empty_perex_count INT NOT NULL,
  empty_keywords_count INT NOT NULL,
  empty_article_content_count INT NOT NULL,
  total_articles_processed_count INT NOT NULL,
  start_article_id INT NOT NULL,
  end_article_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE article_processed_data (
  id SERIAL PRIMARY KEY,
  website_domain VARCHAR(100) NOT NULL,
  article_metadata_id INT,
  article_processing_summary_id INT,
  filename TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
)