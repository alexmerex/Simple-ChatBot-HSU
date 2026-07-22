import pytest

from chatbot_hsu.config import ChatbotConfig


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"mode": "server"}, "MODE"),
        ({"retrieval_k": 0}, "top-k"),
        ({"similarity_threshold": 1.1}, "THRESHOLD"),
        ({"web_timeout_seconds": 0}, "Web limits"),
    ],
)
def test_invalid_config_is_rejected(override, message):
    with pytest.raises(ValueError, match=message):
        ChatbotConfig(**override)


def test_allowed_domains_are_normalized():
    config = ChatbotConfig(web_allowed_domains=(".HOASEN.EDU.VN", ""))

    assert config.web_allowed_domains == ("hoasen.edu.vn",)


def test_invalid_boolean_environment_value_is_rejected_on_config_creation(monkeypatch):
    monkeypatch.setenv("CHATBOT_WEB_ENABLED", "sometimes")

    with pytest.raises(ValueError, match="CHATBOT_WEB_ENABLED"):
        ChatbotConfig()
