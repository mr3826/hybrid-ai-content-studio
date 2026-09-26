import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_platform_settings_and_https_validation(client: AsyncClient):
    # 1. Fetch platforms (seeds 4 default platforms: youtube, facebook, instagram, tiktok)
    res = await client.get("/api/v1/platforms")
    assert res.status_code == 200
    platforms = res.json()
    assert "youtube" in platforms
    assert "facebook" in platforms
    assert "instagram" in platforms
    assert "tiktok" in platforms

    # 2. Update YouTube with valid HTTPS URLs
    yt_payload = {
        "platform": "youtube",
        "channel_name": "Practical AI Studio",
        "channel_url": "https://www.youtube.com/@practicalaistudio",
        "publishing_url": "https://studio.youtube.com/",
        "account_handle": "@practicalaistudio",
        "is_active": True,
    }
    update_res = await client.put("/api/v1/platforms/youtube", json=yt_payload)
    assert update_res.status_code == 200
    yt_data = update_res.json()
    assert yt_data["channel_url"] == "https://www.youtube.com/@practicalaistudio"

    # 3. Validation rejection: Non-HTTPS URL should fail validation
    invalid_payload = {
        "platform": "youtube",
        "channel_name": "Insecure Channel",
        "channel_url": "http://insecure.example.com",
        "publishing_url": "https://studio.youtube.com/",
    }
    bad_res = await client.put("/api/v1/platforms/youtube", json=invalid_payload)
    assert bad_res.status_code in (400, 422)

    # 4. Unknown platform rejection
    unknown_res = await client.put(
        "/api/v1/platforms/myspace",
        json={"platform": "myspace", "channel_name": "Old"},
    )
    assert unknown_res.status_code in (400, 422)
