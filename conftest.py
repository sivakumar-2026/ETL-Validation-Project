"""Shared fixtures: env-based DB engines + local SparkSession."""

from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}. Copy .env.example to .env")
    return value


MSSQL_HOST = _require("MSSQL_HOST")
MSSQL_PORT = _require("MSSQL_PORT")
MSSQL_DATABASE = _require("MSSQL_DATABASE")
MSSQL_USER = _require("MSSQL_USER")
MSSQL_PASSWORD = _require("MSSQL_PASSWORD")
MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
MSSQL_TRUST = os.getenv("MSSQL_TRUST_SERVER_CERTIFICATE", "yes")

POSTGRES_HOST = _require("POSTGRES_HOST")
POSTGRES_PORT = _require("POSTGRES_PORT")
POSTGRES_DATABASE = _require("POSTGRES_DATABASE")
POSTGRES_USER = _require("POSTGRES_USER")
POSTGRES_PASSWORD = _require("POSTGRES_PASSWORD")

SRC_TABLE = os.getenv("SRC_TABLE", "dbo.Album")
TGT_TABLE = os.getenv("TGT_TABLE", "public.album")
PRIMARY_KEY = os.getenv("PRIMARY_KEY", "ALBUMID").upper()

MSSQL_JDBC_JAR = os.getenv("MSSQL_JDBC_JAR", "")
POSTGRES_JDBC_JAR = os.getenv("POSTGRES_JDBC_JAR", "")


def _mssql_odbc_connect() -> str:
    return urllib.parse.quote_plus(
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_HOST},{MSSQL_PORT};"
        f"DATABASE={MSSQL_DATABASE};"
        f"UID={MSSQL_USER};"
        f"PWD={MSSQL_PASSWORD};"
        f"TrustServerCertificate={MSSQL_TRUST};"
    )


def build_mssql_engine():
    return create_engine(f"mssql+pyodbc:///?odbc_connect={_mssql_odbc_connect()}")


def build_postgres_engine():
    pg_pass = urllib.parse.quote_plus(POSTGRES_PASSWORD)
    return create_engine(
        f"postgresql+psycopg2://{POSTGRES_USER}:{pg_pass}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
    )


SRC_ENGINE = build_mssql_engine()
TGT_ENGINE = build_postgres_engine()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Uppercase and strip underscores so AlbumId ~ album_id -> ALBUMID."""
    df = df.copy()
    df.columns = [c.upper().replace("_", "") for c in df.columns]
    return df


def sql_count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


@pytest.fixture(scope="module")
def get_data():
    """Load source and target tables with standardized column names (Pandas)."""
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


@pytest.fixture(scope="session")
def spark():
    """Local SparkSession with MSSQL + Postgres JDBC drivers."""
    jars = ",".join(p for p in [MSSQL_JDBC_JAR, POSTGRES_JDBC_JAR] if p)
    if not jars:
        pytest.skip("MSSQL_JDBC_JAR / POSTGRES_JDBC_JAR not set in .env")

    session = (
        SparkSession.builder.master("local[*]")
        .appName("etl-sourcedb-validation")
        .config("spark.jars", jars)
        .config("spark.driver.extraClassPath", jars)
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture(scope="module")
def spark_frames(spark):
    """Load source/target via JDBC and normalize column names to uppercase."""
    src = (
        spark.read.format("jdbc")
        .option(
            "url",
            f"jdbc:sqlserver://{MSSQL_HOST}:{MSSQL_PORT};"
            f"databaseName={MSSQL_DATABASE};"
            f"encrypt=true;trustServerCertificate=true",
        )
        .option("dbtable", SRC_TABLE)
        .option("user", MSSQL_USER)
        .option("password", MSSQL_PASSWORD)
        .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver")
        .load()
    )

    tgt = (
        spark.read.format("jdbc")
        .option(
            "url",
            f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}",
        )
        .option("dbtable", TGT_TABLE)
        .option("user", POSTGRES_USER)
        .option("password", POSTGRES_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .load()
    )

    for col_name in src.columns:
        src = src.withColumnRenamed(col_name, col_name.upper().replace("_", ""))
    for col_name in tgt.columns:
        tgt = tgt.withColumnRenamed(col_name, col_name.upper().replace("_", ""))

    return src, tgt
