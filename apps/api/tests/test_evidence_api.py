import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evidence_provenance_lifecycle_and_gate(client: AsyncClient):
    test_id = uuid.uuid4().hex[:8]

    # 1. Create Claims with diverse categories
    claim1_payload = {
        "text": f"Apple Silicon M4 Max achieves 138 tokens/s on DeepSeek-R1-67B ({test_id})",
        "claim_type": "external_fact",
        "confidence": 0.95,
    }
    c1_res = await client.post("/api/v1/evidence/claims", json=claim1_payload)
    assert c1_res.status_code == 201
    claim1 = c1_res.json()
    claim1_id = claim1["id"]
    assert claim1["claim_type"] == "external_fact"
    assert claim1["is_verified"] is False

    # Claim 2: initially created as external_fact, will be labeled as opinion
    claim2_payload = {
        "text": f"M4 Max is the undisputed best developer laptop ever built ({test_id})",
        "claim_type": "external_fact",
        "confidence": 0.8,
    }
    c2_res = await client.post("/api/v1/evidence/claims", json=claim2_payload)
    assert c2_res.status_code == 201
    claim2_id = c2_res.json()["id"]

    # Claim 3: factual claim that starts unsupported
    claim3_payload = {
        "text": f"Studio temperature was reduced by 15% using liquid cooling apparatus ({test_id})",
        "claim_type": "external_fact",
        "confidence": 0.9,
    }
    c3_res = await client.post("/api/v1/evidence/claims", json=claim3_payload)
    assert c3_res.status_code == 201
    claim3_id = c3_res.json()["id"]

    # 2. Link Citation Source to Claim 1
    link_payload = {
        "source_url": f"https://hardware-labs.org/benchmarks-{test_id}",
        "source_title": "Mac M4 Max Inference Evaluation",
        "source_type": "primary",
        "trust_weight": 1.4,
        "quote": "Our tests confirmed 138 tokens/second throughput on quantized 67B models.",
        "confidence": 0.98,
        "notes": "Verified against raw terminal logs.",
    }
    link_res = await client.post(f"/api/v1/evidence/claims/{claim1_id}/link-source", json=link_payload)
    assert link_res.status_code == 200
    assert link_res.json()["is_claim_verified"] is True

    # 3. Label Claim 2 as Opinion
    label_res = await client.post(f"/api/v1/evidence/claims/{claim2_id}/label-opinion", json={"claim_type": "opinion"})
    assert label_res.status_code == 200
    assert label_res.json()["claim_type"] == "opinion"

    # 4. Create Experiment and Empirical Measurements for Claim 1
    exp_payload = {
        "title": f"Local Inference Stress Test {test_id}",
        "hypothesis": "M4 Max maintains >130 tok/s without thermal throttling after 30 minutes.",
        "method": "Execute continuous generation loop on Ollama 0.5.4 with batch size 1.",
        "tools_models": ["Ollama", "DeepSeek-R1-67B-Q4_K_M"],
        "parameters": {"batch_size": 1, "context_length": 4096},
    }
    exp_res = await client.post("/api/v1/evidence/experiments", json=exp_payload)
    assert exp_res.status_code == 201
    exp_id = exp_res.json()["id"]

    # Record Run with quantitative empirical measurements
    run_payload = {
        "run_number": 1,
        "execution_time_ms": 1800000,
        "cost_usd": 0.0,
        "status": "success",
        "measurements": [
            {
                "metric": "tokens_per_second",
                "value": 138.2,
                "unit": "tok/s",
                "context": "Average across 50 iterations",
            },
            {
                "metric": "first_token_latency",
                "value": 14.2,
                "unit": "ms",
                "context": "Prompt processing latency",
            },
        ],
    }
    run_res = await client.post(f"/api/v1/evidence/experiments/{exp_id}/runs", json=run_payload)
    assert run_res.status_code == 200
    assert run_res.json()["measurement_count"] == 2

    # Synthesize Conclusion linked to Claim 1
    conclusion_payload = {
        "summary": "M4 Max comfortably sustains 138.2 tok/s with negligible thermal degradation.",
        "claim_id": claim1_id,
        "confidence": 0.99,
    }
    conc_res = await client.post(f"/api/v1/evidence/experiments/{exp_id}/conclusions", json=conclusion_payload)
    assert conc_res.status_code == 200

    # 5. Full Provenance Graph Traversal
    prov_res = await client.get(f"/api/v1/evidence/claims/{claim1_id}/provenance")
    assert prov_res.status_code == 200
    trace = prov_res.json()
    assert trace["claim_id"] == claim1_id
    assert len(trace["sources"]) >= 1
    assert trace["sources"][0]["domain"] == "hardware-labs.org"
    assert len(trace["experiments"]) >= 1
    assert trace["experiments"][0]["experiment_id"] == exp_id
    assert len(trace["experiments"][0]["runs"][0]["measurements"]) == 2

    # 6. Map Claims to Content/Script Section
    content_id = f"script-{test_id}"
    map1_res = await client.post(
        f"/api/v1/evidence/content-claims?claim_id={claim1_id}&content_id={content_id}&quote_in_script=The+M4+Max+hit+138+tok/s&section_id=evidence"
    )
    assert map1_res.status_code == 200
    assert map1_res.json()["verification_status"] == "verified"

    map3_res = await client.post(
        f"/api/v1/evidence/content-claims?claim_id={claim3_id}&content_id={content_id}&quote_in_script=We+lowered+temperatures+by+15%25&section_id=result"
    )
    assert map3_res.status_code == 200
    cc3 = map3_res.json()
    cc3_id = cc3["id"]
    assert cc3["verification_status"] == "unsupported"

    # 7. Check Evidence Coverage (Gate should be BLOCKED because claim 3 is unsupported)
    cov_res = await client.post(f"/api/v1/evidence/coverage?content_id={content_id}")
    assert cov_res.status_code == 200
    report = cov_res.json()
    assert report["total_claims"] == 2
    assert report["unsupported"] == 1
    assert report["gate_passed"] is False

    # 8. Human Creator Override for Claim 3 with mandatory reason
    override_payload = {
        "override_reason": "Verified via direct technician thermocouple measurements during studio lab session.",
    }
    over_res = await client.post(f"/api/v1/evidence/content-claims/{cc3_id}/override", json=override_payload)
    assert over_res.status_code == 200
    assert over_res.json()["is_overridden"] is True
    assert over_res.json()["verification_status"] == "overridden"

    # 9. Verify Gate Now Passes
    cov_after_res = await client.post(f"/api/v1/evidence/coverage?content_id={content_id}")
    assert cov_after_res.status_code == 200
    report_after = cov_after_res.json()
    assert report_after["unsupported"] == 0
    assert report_after["overridden_count"] == 1
    assert report_after["coverage_percent"] == 100.0
    assert report_after["gate_passed"] is True
