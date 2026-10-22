# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Ingest SOP PDFs into Databricks AI Search
# MAGIC
# MAGIC Works on **Databricks Free Edition** (serverless, one AI Search endpoint) and on a full workspace.
# MAGIC
# MAGIC **Before running**
# MAGIC 1. Add this GitHub repo as a **Git folder** (Workspace → Create → Git folder).
# MAGIC 2. Run the first cells to create the schema + volume, then upload `data/sops/*.pdf` into the volume
# MAGIC    (Catalog → your volume → Upload). Re-run the notebook after uploading.
# MAGIC
# MAGIC **What it does**: PDF → section chunks (same chunker as the laptop code) → Delta table with Change Data Feed
# MAGIC → Delta Sync index whose embeddings Databricks computes → test query.

# COMMAND ----------

# MAGIC %pip install -q pypdf databricks-ai-search
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")          # Free Edition's default catalog is `workspace`
dbutils.widgets.text("schema", "mlops_sop")
dbutils.widgets.text("volume", "sop_docs")
dbutils.widgets.text("endpoint", "sop-search-endpoint")
dbutils.widgets.text("embedding_endpoint", "databricks-gte-large-en")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
VOLUME = dbutils.widgets.get("volume")
ENDPOINT = dbutils.widgets.get("endpoint")
EMBEDDING_ENDPOINT = dbutils.widgets.get("embedding_endpoint")

SOURCE_TABLE = f"{CATALOG}.{SCHEMA}.sop_chunks"
INDEX_NAME = f"{CATALOG}.{SCHEMA}.sop_chunks_index"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")
print("Upload the SOP PDFs to:", VOLUME_PATH)

# COMMAND ----------

# Reuse the repo's chunker: this notebook lives in <repo>/databricks/, the package in <repo>/src/
import os, sys
repo_src = os.path.abspath(os.path.join(os.getcwd(), "..", "src"))
if repo_src not in sys.path:
    sys.path.insert(0, repo_src)

from sop_matcher.chunking import chunk_folder

chunks = chunk_folder(VOLUME_PATH)
assert chunks, f"No PDFs found in {VOLUME_PATH} - upload them first"
print(f"{len(chunks)} chunks from {len({c.sop_id for c in chunks})} SOPs")

# COMMAND ----------

from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

schema = StructType([
    StructField("chunk_id", StringType(), False),
    StructField("sop_id", StringType()),
    StructField("sop_title", StringType()),
    StructField("section_no", IntegerType()),
    StructField("section", StringType()),
    StructField("weight", DoubleType()),
    StructField("text", StringType()),
    StructField("source_file", StringType()),
])
df = spark.createDataFrame([c.to_dict() for c in chunks], schema)
df.createOrReplaceTempView("new_chunks")

# MERGE keeps the table in step with the PDFs (updates, inserts, deletes) and gives the
# index a clean change feed. Change Data Feed is required for Delta Sync indexes.
spark.sql(f"""
  CREATE TABLE IF NOT EXISTS {SOURCE_TABLE} (
    chunk_id STRING NOT NULL, sop_id STRING, sop_title STRING, section_no INT,
    section STRING, weight DOUBLE, text STRING, source_file STRING)
  TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")
spark.sql(f"""
  MERGE INTO {SOURCE_TABLE} t USING new_chunks s ON t.chunk_id = s.chunk_id
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *
  WHEN NOT MATCHED BY SOURCE THEN DELETE
""")
display(spark.table(SOURCE_TABLE).select("chunk_id", "section", "weight"))

# COMMAND ----------

import time
from databricks.ai_search.client import AISearchClient

client = AISearchClient(disable_notice=True)

# Endpoint (Free Edition allows exactly one)
existing = [e["name"] for e in client.list_endpoints().get("endpoints", [])]
if ENDPOINT not in existing:
    client.create_endpoint(name=ENDPOINT, endpoint_type="STANDARD")
while client.get_endpoint(ENDPOINT).get("endpoint_status", {}).get("state") != "ONLINE":
    print("waiting for endpoint..."); time.sleep(30)
print("endpoint online:", ENDPOINT)

# COMMAND ----------

# Delta Sync index; Databricks embeds the `text` column with EMBEDDING_ENDPOINT
try:
    index = client.get_index(endpoint_name=ENDPOINT, index_name=INDEX_NAME)
    index.sync()                        # TRIGGERED pipeline: pick up table changes
    print("index exists, sync triggered")
except Exception:
    index = client.create_delta_sync_index(
        endpoint_name=ENDPOINT,
        index_name=INDEX_NAME,
        source_table_name=SOURCE_TABLE,
        pipeline_type="TRIGGERED",
        primary_key="chunk_id",
        embedding_source_column="text",
        embedding_model_endpoint_name=EMBEDDING_ENDPOINT,
    )
    print("index created")

index.wait_until_ready(verbose=True)

# COMMAND ----------

# Smoke test
res = index.similarity_search(
    query_text="create a new service principal for a scheduled batch job",
    columns=["chunk_id", "sop_id", "section"],
    num_results=5,
    query_type="hybrid",
)
for row in res["result"]["data_array"]:
    print(row)
