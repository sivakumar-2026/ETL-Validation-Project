# ETL QA Validation

Automated quality gate for an Album migration from SQL Server to PostgreSQL. Pytest checks counts, keys, nulls, schema, and cell values. Results become an HTML dashboard, a color PDF, and an email.

## What we are doing

Chinook **Album** data is loaded from SQL Server into PostgreSQL. This project does not perform that load. It proves the load is correct.

| Side | Database | Table |
| --- | --- | --- |
| Source | SQL Server `Sourcedb` | `dbo.Album` |
| Target | PostgreSQL `Targetdb` | `public.album` |

Each run answers:

- Did every row arrive?
- Are primary keys unique, with no keys missing or extra?
- Are mandatory columns (`ALBUMID`, `TITLE`, `ARTISTID`) free of nulls?
- Do column names match after `AlbumId` / `album_id` are normalized to `ALBUMID`?
- Do the cell values match?

A failure is reported in the HTML dashboard, the PDF, and the email, including the failing rows.

## Architecture

```text
SQL Server Sourcedb  --ETL load-->  PostgreSQL Targetdb
        |                                    |
        +---------- ODBC / JDBC / SQLAlchemy +
                             |
                  Pytest  (Pandas + PySpark)
                             |
          HTML dashboard  |  Color PDF  |  Plain-text email
                             |
        GitHub Actions (self-hosted Mac)  +  Gmail SMTP
```

1. A trigger starts the run: manual, git push, the daily clock, or a database change.
2. A fingerprint is taken: `COUNT(*)` and `MAX(primary key)` on source and target.
3. Pytest loads both tables and runs the checks.
4. The reporter writes `reports/validation_dashboard.html` and `reports/validation_summary.json`.
5. Playwright prints that same HTML to a color PDF.
6. Gmail sends a plain-text log of every pass and fail, with the PDF attached.

The 15-minute poll only runs the full suite when the fingerprint changed. Push, manual, and daily runs always validate.

| Run type | When |
| --- | --- |
| Manual | `python3 run_dashboard.py` or GitHub **Run workflow** |
| CI Push | Push or pull request |
| Daily RUN | 8:10 AM IST (GitHub schedule on `main`) |
| Automatic Validation | Every 15 minutes, only if the fingerprint changed |

GitHub scheduled workflows run only from the default branch (`main`). The job needs the self-hosted Mac runner because the databases are on localhost.

## Tech stack

| Piece | Role |
| --- | --- |
| Python 3 | Test and report code |
| Pytest | Test runner, fixtures, and the result-collection plugin |
| Pandas | In-memory counts, nulls, schema, and cell-by-cell compare |
| PySpark | Same checks through JDBC, the path used for larger tables |
| SQLAlchemy, pyodbc, psycopg2 | SQL Server and PostgreSQL connections |
| python-dotenv | Reads `.env` (copy from `.env.example`) |
| HTML / CSS / JS | Interactive dashboard |
| Playwright | Color PDF that matches the browser report |
| Gmail SMTP | Alert email (`certifi` for TLS on macOS) |
| GitHub Actions | Push, schedule, and manual CI on a self-hosted runner |
| Jenkins | Optional daily pipeline (`Jenkinsfile`) |

## Run it locally

```bash
cp .env.example .env
# fill in database and SMTP values
python3 run_dashboard.py
```

That validates, opens the dashboard in the browser, and sends the email. The subject says **Manual**.
