# GitHub Actions secrets for ETL validation

Add these under: **Repo → Settings → Secrets and variables → Actions**

## Database
| Secret | Example |
|--------|---------|
| `MSSQL_HOST` | `localhost` (or `host.docker.internal` if needed) |
| `MSSQL_PORT` | `1433` |
| `MSSQL_DATABASE` | `Sourcedb` |
| `MSSQL_USER` | `sa` |
| `MSSQL_PASSWORD` | *(your password)* |
| `MSSQL_DRIVER` | `ODBC Driver 18 for SQL Server` |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_DATABASE` | `Targetdb` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | *(your password)* |
| `SRC_TABLE` | `dbo.Album` |
| `TGT_TABLE` | `public.album` |
| `PRIMARY_KEY` | `ALBUMID` |
| `MSSQL_JDBC_JAR` | absolute path on the runner Mac |
| `POSTGRES_JDBC_JAR` | absolute path on the runner Mac |

## Email
| Secret | Example |
|--------|---------|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `sivakumartorur@gmail.com` |
| `SMTP_PASSWORD` | Gmail App Password |
| `SMTP_FROM` | `sivakumartorur@gmail.com` |
| `ALERT_EMAIL` | `sivakumartorur@gmail.com` |

## Self-hosted runner (required)
GitHub-hosted runners cannot reach DBs on your laptop.

1. Repo → **Settings → Actions → Runners → New self-hosted runner**
2. Choose **macOS**, follow install steps on the Mac where Docker SQL/Postgres run
3. Keep the runner process online (`./run.sh` or install as service)
4. Push to `main` / `etl-db-migration-project` → workflow runs → email with PDF
