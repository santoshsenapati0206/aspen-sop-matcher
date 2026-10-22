# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Match an ASPEN ticket to its SOP (inside Databricks)
# MAGIC Same matcher as the laptop CLI, using the AI Search index built by `01_ingest_sops`.

# COMMAND ----------

# MAGIC %pip install -q pypdf databricks-ai-search scikit-learn
# MAGIC %restart_python

# COMMAND ----------

import json, os, sys
repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
sys.path.insert(0, os.path.join(repo_root, "src"))

from sop_matcher.matcher import match_ticket
from sop_matcher.retrievers.databricks_ai_search import DatabricksAISearchRetriever
from sop_matcher.ticket import Ticket

retriever = DatabricksAISearchRetriever(
    host=None, token=None,                       # auto-detected inside a notebook
    endpoint="sop-search-endpoint",
    index_name="workspace.mlops_sop.sop_chunks_index",
    query_type="hybrid",
)

for name in ["ASPEN-1001.json", "ASPEN-1002.json"]:
    result = match_ticket(Ticket.from_file(os.path.join(repo_root, "data", "tickets", name)), retriever)
    print(json.dumps({k: result.to_dict()[k] for k in ("ticket_id", "status", "sop_id", "confidence")}))
