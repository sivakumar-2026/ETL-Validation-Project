import urllib.parse

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

# SOURCE: SQL Server (TestDB)
MSSQL_PARAMS = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=TestDB;"
    "UID=sa;"
    "PWD=Filmmaker@2024;"
    "TrustServerCertificate=yes;"
)
SRC_ENGINE = create_engine(f"mssql+pyodbc:///?odbc_connect={MSSQL_PARAMS}")

# TARGET: Postgres (Docker)
PG_PASS = urllib.parse.quote_plus("Tester@2024")
TGT_ENGINE = create_engine(f"postgresql+psycopg2://postgres:{PG_PASS}@localhost:5432/postgres")

SRC_TABLE = "dbo.Movies"
TGT_TABLE = "public.Movies"
PRIMARY_KEY = "MOVIEID"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]
    return df


def sql_count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


@pytest.fixture(scope="module")
def get_data():
    """Load source and target tables with standardized column names."""
    df_src = _normalize_columns(pd.read_sql(f"SELECT * FROM {SRC_TABLE}", SRC_ENGINE))
    df_tgt = _normalize_columns(pd.read_sql(f"SELECT * FROM {TGT_TABLE}", TGT_ENGINE))
    return df_src, df_tgt


@pytest.fixture(scope="module")
def table_counts():
    """Return SQL-level row counts for source and target tables."""
    return {
        "source": sql_count(SRC_ENGINE, SRC_TABLE),
        "target": sql_count(TGT_ENGINE, TGT_TABLE),
    }
