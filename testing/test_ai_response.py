import asyncio
from backend.ai import get_ai_data


def test_ai_response():
    complaint = "my laptop is not working . the display has gone off"
    d = asyncio.run(get_ai_data(complaint))
    assert isinstance(d, dict)
    assert d.get('category') == 'Hardware'
    assert d.get('priority') is not None
    assert d.get('suggested_fix')










