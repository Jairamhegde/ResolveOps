import asyncio
import pytest
from backend.ai import get_ai_data


NOT_IT_ISSUE_FLAGS = {"spam", "unclear"}


@pytest.mark.ai
def test_ai_response():
    complaint1 = "my laptop is not working . the display has gone off"
    complaint2 = "How are you."
    complaint3 = "I will beat you"
    complaint4 = "Iam feeling sleepy"
    complaint5 = "VPN Connection is not working, and my laptop also got shut down"

    async def run_all():
        return await asyncio.gather(
            get_ai_data(complaint1),
            get_ai_data(complaint2),
            get_ai_data(complaint3),
            get_ai_data(complaint4),
            get_ai_data(complaint5)
        )

    laptop, greeting, threat, sleepy, vpn_and_laptop = asyncio.run(run_all())

    assert laptop, "AI call failed for complaint1"
    assert laptop["category"] == "hardware"
    assert laptop["priority"] <= 3
    assert laptop["flag"] == "none"
    assert laptop["suggested_fix"]

    assert greeting, "AI call failed for complaint2"
    assert greeting["category"] == "other"
    assert greeting["flag"] in NOT_IT_ISSUE_FLAGS

    assert threat, "AI call failed for complaint3"
    assert threat["category"] == "other"
    assert threat["flag"] in NOT_IT_ISSUE_FLAGS

    assert sleepy, "AI call failed for complaint4"
    assert sleepy["category"] == "other"
    assert sleepy["flag"] in NOT_IT_ISSUE_FLAGS

    assert vpn_and_laptop, "AI call failed for complaint5"
    assert vpn_and_laptop["category"] in {"network", "hardware"}
    assert vpn_and_laptop["flag"] == "none"
    assert vpn_and_laptop["suggested_fix"]
