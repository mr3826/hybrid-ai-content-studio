import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_research_packet_lifecycle_and_revisions(client: AsyncClient):
    test_id = uuid.uuid4().hex[:8]

    # 1. Generate Research Packet with rich sources
    sources = [
        {
            "url": f"https://techbenchmark.io/apple-m4-deepseek-{test_id}",
            "title": "M4 Max DeepSeek 67B Local Inference Analysis",
            "excerpt": (
                "DeepSeek on Mac M4 Max achieved 138 tokens/s with 14ms first-token latency on 2026-03-01. "
                "The engine delivers a +180% speedup vs previous generation. "
                "However, memory bandwidth might be saturated with 4 concurrent batches."
            ),
            "trust_weight": 1.5,
        },
        {
            "url": f"https://independent-lab.net/m4-stress-test-{test_id}",
            "title": "Independent Stress Tests of Apple Silicon",
            "excerpt": (
                "Under thermal stress, latency spiked to 42ms. "
                "The vendor claims this system is 100% bug-free and completely replaces human engineers."
            ),
            "trust_weight": 1.0,
        },
    ]

    create_payload = {
        "topic": f"Apple Silicon M4 Max LLM Inference Benchmarks {test_id}",
        "sources": sources,
        "context": "Hardware testing in local studio lab.",
    }

    create_res = await client.post("/api/v1/research/packets", json=create_payload)
    assert create_res.status_code == 201
    packet = create_res.json()
    packet_id = packet["id"]

    # Verify acceptance criteria & components
    assert packet["topic"] == create_payload["topic"]
    assert len(packet["primary_sources"]) >= 1
    assert len(packet["supporting_sources"]) >= 1
    assert len(packet["facts"]) >= 1
    assert len(packet["numbers"]) >= 2
    assert len(packet["dates"]) >= 1
    assert len(packet["entities"]) >= 1
    assert len(packet["things_not_to_claim"]) >= 1
    assert len(packet["contradictions"]) >= 1  # 14ms vs 42ms
    assert packet["version"] == 1
    assert packet["is_verified"] is False

    # Check claim classification invariant
    valid_statuses = {"source-backed", "explicitly_uncertain", "manually_entered"}
    for claim in packet["claims"]:
        assert claim["verification_status"] in valid_statuses
        if claim["verification_status"] == "source-backed":
            assert claim["source_url"] is not None
            assert claim["evidence_quote"] is not None
        elif claim["verification_status"] == "explicitly_uncertain":
            assert claim["uncertainty_reason"] is not None

    # 2. List Packets
    list_res = await client.get("/api/v1/research/packets?limit=20")
    assert list_res.status_code == 200
    packets_list = list_res.json()
    assert any(p["id"] == packet_id for p in packets_list)

    # 3. Get Packet Detail
    detail_res = await client.get(f"/api/v1/research/packets/{packet_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == packet_id

    # 4. Manual Corrections by Creator (preserving revisions)
    existing_claims = detail["claims"]
    manual_claim = {
        "id": "manual-1",
        "claim_text": "Local temperature remained under 65C during 2-hour stress test.",
        "verification_status": "manually_entered",
        "confidence": 1.0,
    }
    updated_claims = existing_claims + [manual_claim]

    update_payload = {
        "summary": "Updated summary with verified studio thermal measurements.",
        "claims": updated_claims,
        "change_summary": "Added creator manual thermal verification claim",
        "changed_by": "lead-creator",
    }
    update_res = await client.put(f"/api/v1/research/packets/{packet_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_packet = update_res.json()
    assert updated_packet["version"] == 2
    assert updated_packet["summary"] == update_payload["summary"]
    assert any(c.get("id") == "manual-1" and c["verification_status"] == "manually_entered" for c in updated_packet["claims"])

    # 5. Check Revisions History
    rev_res = await client.get(f"/api/v1/research/packets/{packet_id}/revisions")
    assert rev_res.status_code == 200
    revisions = rev_res.json()
    assert len(revisions) >= 2  # initial revision 1 + updated revision
    rev_numbers = [r["revision_number"] for r in revisions]
    assert 1 in rev_numbers

    # 6. Human Gate Verification
    verify_res = await client.post(f"/api/v1/research/packets/{packet_id}/verify")
    assert verify_res.status_code == 200
    verified_packet = verify_res.json()
    assert verified_packet["is_verified"] is True
    assert verified_packet["verified_at"] is not None
    assert verified_packet["verified_by"] == "creator"

    # 7. Revert to Revision 1
    revert_res = await client.post(f"/api/v1/research/packets/{packet_id}/revert/1")
    assert revert_res.status_code == 200
    reverted_packet = revert_res.json()
    assert reverted_packet["version"] == 3
    # In revision 1, our manual thermal claim was not present
    assert not any(c.get("id") == "manual-1" for c in reverted_packet["claims"])


@pytest.mark.asyncio
async def test_research_packet_linked_to_opportunity(client: AsyncClient):
    test_id = uuid.uuid4().hex[:8]

    # Create Opportunity via Opportunity Engine
    run_payload = {
        "custom_topics": [
            {
                "topic": f"Local Ollama vs vLLM Serving Benchmark {test_id}",
                "summary": "Comprehensive comparison of throughput, concurrency, and memory footprints.",
                "pillar": "AI Tooling",
                "trend_score": 85.0,
                "sources": [
                    {
                        "url": f"https://benchmarks.local/ollama-vllm-{test_id}",
                        "title": "Serving Benchmarks",
                        "excerpt": "Ollama scored 112 tokens/s; vLLM scored 145 tokens/s on same hardware on 2026-03-10.",
                        "trust_weight": 1.2,
                    }
                ],
            }
        ],
        "include_candidates": False,
        "include_trends": False,
    }
    await client.post("/api/v1/opportunities/run", json=run_payload)
    list_opps = (await client.get("/api/v1/opportunities?limit=20")).json()
    matching_opp = next(o for o in list_opps if test_id in o["topic"])
    opp_id = matching_opp["id"]

    # Mark opportunity as research_ready
    await client.post(f"/api/v1/opportunities/{opp_id}/research")

    # Generate research packet for this opportunity
    gen_res = await client.post("/api/v1/research/packets", json={"opportunity_id": opp_id})
    assert gen_res.status_code == 201
    packet = gen_res.json()
    assert packet["opportunity_id"] == opp_id
    assert packet["is_verified"] is False
    assert len(packet["numbers"]) >= 2

    # Human Gate: verify the research packet
    verify_res = await client.post(f"/api/v1/research/packets/{packet['id']}/verify")
    assert verify_res.status_code == 200
    assert verify_res.json()["is_verified"] is True

    # Linked opportunity workflow status should now be updated to in_production
    opp_detail = (await client.get(f"/api/v1/opportunities/{opp_id}")).json()
    assert opp_detail["status"] == "in_production"
