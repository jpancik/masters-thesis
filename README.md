# Project Webtrack
## Dezinfo website crawler
This is a website crawler that specializes in regular crawling of media websites. Its aim is to provide a simple
platform for tracking media websites that publish content containing disinformation/propaganda/fake news/hoax.

It can extract URLs for articles from specified domains. It can extract pure article text and other metadata e.g.
author, a publication date, keywords via templates. It stores data in a JSON format and in a vertical file format, that
is suitable to be compiled into a text corpora.

#### Setting up the website crawler
Prerequisites:
1. POSIX-friendly OS. (Tested with macOS 10.14.4 and Fedora 28.)
2. Python 3 with pip installed.

Steps:
1. Install Python libraries via command `pip install -r requirements.txt`. Use of virtualenv is recommended.
2. Obtain a DB password for Postgres database and put it into `files/db_password` on the first line. To change the connection string, modify `lib/crawler_db/connector.py`.
3. If necessary, set up new tables in Postgres database. SQL commands to do so are available in `files/sql_commands.sql`.

#### Crawler scripts
Each script in `scripts/` folder is runnable via command line, with `python scripts/<script.py>` format. To get
documentation about available command line args, run the script with `python scripts/<script.py> --help`.

Scripts should be run in this order, but it's not necessary:
1. `scripts/gather_articles_metadata.py` – Downloads URLs for articles from monitored website domains. Data is stored into DB in `articles_metadata` table.
2. `scripts/download_articles.py` – Download raw HTML files for each article URL gathered, that has not been yet downloaded. HTMl files are stored in `data/raw_articles/` and in DB in `articles_raw_html` table.
3. `scripts/process_articles.py` – Extracts pure data from raw HTML files and stores them into JSON files under `data/processed_articles/` folder. Also a record is inserted into `data/article_processed_data/`.
4. `scripts/watchdog.py` – Automatically checks last article processing results if there are any problems. JSON file with results is stored into `data/watchdog_output.json`.
5. `scripts/create_preverticals.py` – Creates prevertical files from processed articles. Preverticals are stored in `data/vertical_files/preverticals`.

#### Regular crawling 
To have the crawler run regularly, set up a cronjobs via `crontab -e` on the machine with wrapper scripts `scripts/gather_and_download_articles.sh` and `scripts/process_articles_and_create_corpus.sh`.

Example usage (output from `crontab -l`), to have the crawler download articles every day at 6am, 12pm, 6pm, 10pm and process articles only on monday at 2pm:
```
05 6,12,18,22 * * * /home/pancik/webtrack/scripts/gather_and_download_articles.sh >> /home/pancik/log_gather_and_download_articles.txt 2>&1
15 14 * * 1 /home/pancik/webtrack/scripts/process_articles_and_create_corpus.sh >> /home/pancik/log_process_articles_and_create_corpus.txt 2>&1
```

#### Add new domain to monitored domains
To add a new domain, add a new entry into `files/website_article_urls_descriptions.json` file. If the domain has RSS
feed, then just add new entry with `rss_url` attribute. If the domain doesn't have a RSS feed, then add new entry that
specifies `"use_regex_parser": true`, list possible URLs that could contain article URLs in `"possible_source": []` and
then specify a regex that `href` attributes on those possible sources have to match in order to be considered as an article URL. If
the domain has a specific encoding, which means you occasionally get wrong characters in raw HTMLs after download, then specify encoding
with `"enconding": "utf-8"`.

Second step is adding a template to extract data from article in `files/website_article_format_descriptions.json` file.
Template consists of several information that the crawler can extract from article. Title, author, date, perex, keywords
all start with specifying CSS selector in `selector`. After that, you can filter out what you get from the selected
tag via either regex on raw tag or regex on text after removing all HTML tags. For article text specified as `article`,
after adding a CSS selector you can remove HTML tags inside that article selector. It's best to look at existing templates
and/or look at the `lib/article_data_extractors/html_extractor.py`.

Last step is adding a subcorpora definition, which is needed for text analysis. You can do that in `files/compilecorp_config/dezinfo_subcdef.txt`.
Just add a new domain with the same structure as there are other website domains.

#### Fixing problems in data found by `scripts/watchdog.py`
If watchdog.py is reporting a lot of errors, especially in high 90% or 100% of articles are missing some sort of
data for certain website domain, then a manual correction of the template that extracts data might be necessary.
First find an article in `data/processed_articles/` for the given domain that is missing given metadata, but in it's 
raw HTML, you can see the data. Then proceed using `python scripts/process_article.py --manual --dry-run --sql-conditions "AND a.id = <article id>"`
to debug your changes to HTML template.

## Text analysis
This project also contains few scripts, that can do analyses on data from the crawler and produce static HTML pages with visualizations.

These analyses are:
* Finding plagiate articles between different website domains
* Analyze how are hyperlinks used to link between articles from different website domains
* Find keywords and terms for website domains
* Find word trends based on time

#### Running the analyses
Steps:
1. Obtain a SketchEngine API username and key and put it into `files/ske_api_key` on the first line in format `<api_username> <api_key>`.
2. Run script `scripts/create_corpus.py`, that will process prevertical files into vertical files and compile a text corpora.
3. Run script `scripts/do_analysis.py` with `--type` argument specifying which analysis you want.
4. Run script `scripts/generate_html.py`, which will generate static website into `data/html/`.

#### Removing Postgres dependency
If needed, it is possible to remove Postgres database dependency from the project. You'll have to modify 
`lib/crawler_db/connector.py` to use sqlite3 connector. Then you have to replace `%s` in every SQL for `?`. Last step 
is changing `scripts/process_articles.py` to use `cursor.lastrowid` instead of `RETURNING id`. 