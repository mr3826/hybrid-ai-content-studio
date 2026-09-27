import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_originality_api_health_and_formats(client: AsyncClient):
    # Health check
    res = await client.get("/api/v1/originality/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # Formats check
    res = await client.get("/api/v1/originality/formats")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 12
    types = [f["type"] for f in data["formats"]]
    assert "tool_test" in types
    assert "benchmark" in types
    assert "failure_analysis" in types
    assert "practical_tutorial" in types
    assert "clearly_labeled_opinion" in types


@pytest.mark.asyncio
async def test_propose_original_angles(client: AsyncClient):
    payload = {
        "topic": "DeepSeek-R1-Distill-Qwen-14B on M4 Pro Mac",
        "summary": "DeepSeek released lightweight reasoning models capable of running on consumer hardware.",
    }
    res = await client.post("/api/v1/originality/propose-angles", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["angles"]) == 3
    assert any(a["originality_type"] == "benchmark" for a in data["angles"])


@pytest.mark.asyncio
async def test_originality_plan_lifecycle_and_approval(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]
    topic = f"Benchmarking llama.cpp vs Ollama Throughput ({test_id})"

    # 1. Create a valid originality plan
    create_payload = {
        "topic": topic,
        "originality_type": "benchmark",
        "what_are_we_adding": "Side-by-side prompt ingestion & generation token speed tests across 5 runs on 64GB Mac.",
        "why_it_matters": "Developers need to know if the Ollama overhead is worth the convenience.",
    }
    res = await client.post("/api/v1/originality/plans", json=create_payload)
    assert res.status_code == 201
    plan = res.json()
    plan_id = plan["id"]
    assert plan["is_generic_summary"] is False
    assert plan["status"] == "needs_review"

    # 2. Approve via Human Quality Gate
    res = await client.post(
        f"/api/v1/originality/plans/{plan_id}/approve",
        json={"reviewer": "chief_editor", "notes": "Solid empirical angle with measurable contribution."},
    )
    assert res.status_code == 200
    approved = res.json()
    assert approved["status"] == "approved"
    assert approved["reviewed_by"] == "chief_editor"

    # 3. Retrieve plan details
    res = await client.get(f"/api/v1/originality/plans/{plan_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["status"] == "approved"
    assert detail["originality_type"] == "benchmark"


@pytest.mark.asyncio
async def test_generic_summary_quarantine_and_rejection(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]
    topic = f"OpenAI Announces GPT-5 Release Date ({test_id})"

    # Create plan that is a generic news recap
    payload = {
        "topic": topic,
        "originality_type": "multi_source_synthesis",
        "what_are_we_adding": "Just a general news summary of the article announcing GPT-5.",
        "why_it_matters": "Keep viewers informed.",
    }
    res = await client.post("/api/v1/originality/plans", json=payload)
    assert res.status_code == 201
    plan = res.json()
    plan_id = plan["id"]
    assert plan["is_generic_summary"] is True
    assert plan["status"] == "not_ready"

    # Human approval MUST fail due to invariant: generic summaries cannot be approved
    approve_res = await client.post(
        f"/api/v1/originality/plans/{plan_id}/approve",
        json={"reviewer": "editor", "notes": "Approved anyway"},
    )
    assert approve_res.status_code == 400
    assert "Cannot approve generic summary" in approve_res.json()["detail"]

    # Reject plan
    reject_res = await client.post(
        f"/api/v1/originality/plans/{plan_id}/reject",
        json={"reason": "Must include original hands-on testing or benchmark data."},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_experiment_workspace_lifecycle_and_evidence_link(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Create Plan
    plan_res = await client.post(
        "/api/v1/originality/plans",
        json={
            "topic": f"Local Ollama VRAM Saturation Test ({test_id})",
            "originality_type": "tool_test",
            "what_are_we_adding": "Measured exact memory allocation curve when serving 32k context on Ollama.",
        },
    )
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    # 2. Create Experiment in Workspace
    exp_payload = {
        "title": f"VRAM Curve at 32k Context ({test_id})",
        "question": "Does Ollama release GPU memory between sequential requests?",
        "hypothesis": "Memory remains allocated due to KV cache pooling.",
        "method": "Execute 10 requests with 4k token payloads and poll nvidia-smi / metal memory every 200ms.",
        "dataset_sample": "Synthetic 4k token Python coding prompts",
        "tools_models": ["Ollama v0.5.4", "DeepSeek-R1-Distill-14B"],
        "parameters": {"num_ctx": 32768, "temperature": 0.2},
        "results": {"peak_vram_gb": 14.8, "cache_retention_pct": 100},
        "failures": ["Context window truncated when payload exceeded 32000 tokens"],
        "latency_ms": 3420.5,
        "cost_usd": 0.0,
        "status": "completed",
        "originality_plan_id": plan_id,
    }
    exp_res = await client.post("/api/v1/originality/experiments", json=exp_payload)
    assert exp_res.status_code == 201
    exp = exp_res.json()
    exp_id = exp["id"]
    assert exp["title"] == exp_payload["title"]
    assert exp["latency_ms"] == 3420.5

    # 3. Add Attachment (CSV benchmark logs)
    att_res = await client.post(
        f"/api/v1/originality/experiments/{exp_id}/attachments",
        json={
            "attachment_type": "csv",
            "filename": "vram_saturation_logs.csv",
            "file_path": "/data/experiments/vram_saturation_logs.csv",
            "mime_type": "text/csv",
            "size_bytes": 10420,
            "content_snippet": "timestamp,step,vram_used_mb\n1710000000,1,8192\n1710000001,2,14820",
            "caption": "Raw Metal memory samples over 10 request cycles",
        },
    )
    assert att_res.status_code == 201
    att = att_res.json()
    assert att["filename"] == "vram_saturation_logs.csv"

    # 4. Link Experiment to Evidence Engine
    evidence_res = await client.post(
        f"/api/v1/originality/experiments/{exp_id}/link-evidence",
        json={
            "conclusion_text": "Ollama retains KV cache memory allocations across sequential requests up to peak context size.",
            "confidence": 0.98,
        },
    )
    assert evidence_res.status_code == 201
    conclusion = evidence_res.json()
    assert conclusion["experiment_id"] == exp_id
    assert "retains KV cache" in conclusion["summary"]

    # 5. Fetch full experiment details
    detail_res = await client.get(f"/api/v1/originality/experiments/{exp_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["attachments"]) == 1
    assert detail["attachments"][0]["filename"] == "vram_saturation_logs.csv"
    assert len(detail["conclusions"]) == 1
    assert detail["conclusions"][0]["confidence"] == 0.98

    # 6. Verify plan reflects experiment
    plan_detail_res = await client.get(f"/api/v1/originality/plans/{plan_id}")
    assert plan_detail_res.status_code == 200
    plan_detail = plan_detail_res.json()
    assert len(plan_detail["experiments"]) == 1
    assert plan_detail["experiments"][0]["id"] == exp_id
