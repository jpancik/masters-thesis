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
)
