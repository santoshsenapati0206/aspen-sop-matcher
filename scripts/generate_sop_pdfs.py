"""Generate the 4 sample SOP PDFs used by the Level 0 prototype.

These stand in for the Confluence SOP pages you can't reach from a personal laptop.
Every SOP follows the same numbered-section layout, which the chunker relies on:

    SOP-<AREA>-<NNN>: <title>
    1. Purpose and Scope
    2. When to use this SOP
    ...

Run:  python scripts/generate_sop_pdfs.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "sops"

SOPS = [
    {
        "file": "SOP-UC-001_unity_catalog_data_access.pdf",
        "id": "SOP-UC-001",
        "title": "Unity Catalog Data Access (Catalog / Schema / Table / View / Function / Volume)",
        "sections": [
            ("Purpose and Scope", [
                "This SOP covers granting or revoking access to Unity Catalog securables in Databricks: "
                "catalogs, schemas, tables, views, SQL functions (UDFs) and volumes.",
                "Typical privileges: USE CATALOG, USE SCHEMA, SELECT, MODIFY, EXECUTE, READ VOLUME, WRITE VOLUME.",
            ]),
            ("When to use this SOP", [
                "A user or AD group needs read (SELECT) or write (MODIFY) access to a table, view or schema.",
                "A user or AD group needs EXECUTE permission on a SQL function or UDF.",
                "Access to data in a lakehouse data product needs to be added, changed or removed.",
            ]),
            ("Not covered by this SOP", [
                "Access to registered ML models or model serving endpoints: use SOP-MDL-004.",
            ]),
            ("Required information in the ticket", [
                "Environment (dev, uat, prod).",
                "Principal type and name. Grants must go to an AD group; individual-user grants need DPO exception.",
                "Fully qualified securable name: catalog.schema.object.",
                "Privilege requested and data product name.",
                "Business justification and access duration.",
            ]),
            ("Validation rules", [
                "Securable must exist in the target environment.",
                "Privilege must be the least required; ALL PRIVILEGES and MANAGE are never granted via ticket.",
                "Prod MODIFY requires an additional JO sign-off.",
                "PII-tagged tables require the requester group to be on the PII-approved list.",
            ]),
            ("Approval", [
                "Data Product Owner (DPO) of the owning data product approves every grant.",
                "Job Owner (JO) approval is additionally required for prod write access.",
            ]),
            ("Implementation", [
                "Repository: lakehouse-policies.",
                "Branch: feature/<ASPEN-ID>-uc-access created from dev.",
                "File: policies/<env>/<catalog>/<schema>.yaml. Add the principal and privilege under the securable's grants block.",
            ]),
            ("Deployment", [
                "Jenkins job: lakehouse-policies-deploy-<env>, triggered after the PR is merged to dev (non-prod) or main (prod).",
            ]),
            ("Post-deployment verification", [
                "Run SHOW GRANTS ON <securable> in the target workspace and confirm the principal and privilege.",
                "Comment the result on the ASPEN ticket and resolve it.",
            ]),
        ],
    },
    {
        "file": "SOP-SP-002_service_principal_creation.pdf",
        "id": "SOP-SP-002",
        "title": "New Service Principal Provisioning (Azure Entra ID + Databricks)",
        "sections": [
            ("Purpose and Scope", [
                "This SOP covers creating a brand-new service principal (application identity) in Azure Entra ID "
                "and registering it in one or more Databricks workspaces.",
                "Service principals are used by automated jobs, workflows, pipelines and CI/CD instead of personal accounts.",
            ]),
            ("When to use this SOP", [
                "A team needs a new automated identity for a scheduled job, batch inference, Databricks Workflow or Jenkins pipeline.",
                "A production job currently runs with personal user credentials and must move to a service principal.",
            ]),
            ("Not covered by this SOP", [
                "Adding people or groups to an EXISTING service principal: use SOP-SP-003.",
            ]),
            ("Required information in the ticket", [
                "Proposed name following convention sp-<team>-<purpose>.",
                "Target environments / workspaces.",
                "Named owner (a permanent employee) and cost center.",
                "Purpose of the identity and whether a client secret is needed.",
            ]),
            ("Validation rules", [
                "Name must match sp-<team>-<purpose> and be unique in the tenant.",
                "Owner must be a permanent employee, not a contractor.",
                "Client secrets have a 180-day expiry and are stored only in Azure Key Vault.",
            ]),
            ("Approval", [
                "Job Owner (JO) of the consuming job approves the creation.",
                "Data Product Owner (DPO) approval is needed only if data grants are requested in the same ticket.",
            ]),
            ("Implementation", [
                "Repository: grey-infra.",
                "Branch: feature/<ASPEN-ID>-new-sp created from master.",
                "File: terraform/service_principals/<sp_name>.tf using module sp_with_databricks_registration.",
            ]),
            ("Deployment", [
                "Jenkins job: grey-infra-terraform-plan on PR, grey-infra-terraform-apply after merge to master.",
            ]),
            ("Post-deployment verification", [
                "Confirm the application exists in Entra ID and the service principal is listed in each Databricks workspace.",
                "Confirm the secret is in Key Vault and share the Key Vault reference (never the secret) on the ASPEN ticket.",
            ]),
        ],
    },
    {
        "file": "SOP-SP-003_service_principal_access.pdf",
        "id": "SOP-SP-003",
        "title": "Access to an Existing Service Principal (Service Principal User / Manager role)",
        "sections": [
            ("Purpose and Scope", [
                "This SOP covers granting a user or group permission to use or manage an EXISTING service principal, "
                "for example to run jobs as the service principal or to rotate its secret.",
            ]),
            ("When to use this SOP", [
                "A user or group needs the Service Principal User role to run a job as an existing service principal.",
                "A user or group needs the Service Principal Manager role, or read access to the service principal secret in Key Vault.",
                "Ownership of an existing service principal must be transferred.",
            ]),
            ("Not covered by this SOP", [
                "Creating a new service principal: use SOP-SP-002.",
            ]),
            ("Required information in the ticket", [
                "Existing service principal name or application ID.",
                "Principal (user or group) to be granted and the role requested.",
                "Environment / workspace and business justification.",
            ]),
            ("Validation rules", [
                "The service principal must already exist.",
                "Manager role is granted only to members of the owning team.",
                "Key Vault secret read is granted only to groups, never to individual users.",
            ]),
            ("Approval", [
                "Current owner of the service principal or the Job Owner (JO) approves.",
            ]),
            ("Implementation", [
                "Repository: grey-infra.",
                "Branch: feature/<ASPEN-ID>-sp-access created from master.",
                "File: terraform/service_principals/<sp_name>.tf. Add the principal to the sp_users or sp_managers list.",
            ]),
            ("Deployment", [
                "Jenkins job: grey-infra-terraform-apply after merge to master.",
            ]),
            ("Post-deployment verification", [
                "Check the service principal's permissions in the Databricks account console and comment on the ASPEN ticket.",
            ]),
        ],
    },
    {
        "file": "SOP-MDL-004_model_access.pdf",
        "id": "SOP-MDL-004",
        "title": "ML Model and Model Serving Endpoint Access",
        "sections": [
            ("Purpose and Scope", [
                "This SOP covers access to machine learning models registered in Unity Catalog and to "
                "Databricks Model Serving endpoints, including foundation model endpoints.",
            ]),
            ("When to use this SOP", [
                "A user, group or service principal needs EXECUTE on a registered model to load it for inference.",
                "A consumer needs CAN_QUERY on a model serving endpoint, or CAN_MANAGE to update the endpoint.",
                "A team needs access to an LLM or foundation model endpoint.",
            ]),
            ("Not covered by this SOP", [
                "Access to tables, schemas or SQL functions: use SOP-UC-001.",
            ]),
            ("Required information in the ticket", [
                "Model full name (catalog.schema.model) or serving endpoint name.",
                "Principal and permission (EXECUTE, CAN_QUERY, CAN_MANAGE).",
                "Environment and expected request volume for serving endpoints.",
            ]),
            ("Validation rules", [
                "Model or endpoint must exist and be in READY state.",
                "CAN_MANAGE is granted only to the owning ML team.",
                "Foundation model endpoints require an approved use-case ID.",
            ]),
            ("Approval", [
                "Model owner / Data Product Owner (DPO) approves.",
            ]),
            ("Implementation", [
                "Repository: quanta-provisioning.",
                "Branch: feature/<ASPEN-ID>-model-access created from dev.",
                "File: data_products/<data_product>/models/<env>.yaml. Add the principal under the model or endpoint permissions block.",
            ]),
            ("Deployment", [
                "Jenkins job: quanta-provisioning-deploy-<env> after merge.",
            ]),
            ("Post-deployment verification", [
                "Query the endpoint permissions API or run SHOW GRANTS ON MODEL and comment on the ASPEN ticket.",
            ]),
        ],
    },
]


def build_pdf(sop: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / sop["file"]
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=f'{sop["id"]}: {sop["title"]}')
    story = [
        Paragraph(f'{sop["id"]}: {sop["title"]}', styles["Title"]),
        Paragraph("Owner: MLOps Platform Team &nbsp;|&nbsp; Version 1.0 &nbsp;|&nbsp; Sample SOP for prototype", styles["Italic"]),
        Spacer(1, 0.4 * cm),
    ]
    for i, (heading, bullets) in enumerate(sop["sections"], start=1):
        story.append(Paragraph(f"{i}. {heading}", styles["Heading2"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(b, styles["BodyText"]), leftIndent=12) for b in bullets],
            bulletType="bullet", start="-",
        ))
        story.append(Spacer(1, 0.2 * cm))
    doc.build(story)
    return path


if __name__ == "__main__":
    for sop in SOPS:
        print("wrote", build_pdf(sop))
