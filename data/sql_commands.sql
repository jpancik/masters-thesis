-- Init tables.
CREATE TABLE article (
  id SERIAL PRIMARY KEY,
  website_domain VARCHAR(100) NOT NULL,
  url VARCHAR(2083) NOT NULL,
  title TEXT,
  publication_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);