import pytest

from app.image_provider import OpenAIImageProvider


def test_provider_rejects_missing_environment_key() -> None:
    provider = OpenAIImageProvider(None)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        provider._read_api_key()


def test_provider_normalizes_environment_key() -> None:
    provider = OpenAIImageProvider("  sk-test-key  ")

    assert provider._read_api_key() == "sk-test-key"
