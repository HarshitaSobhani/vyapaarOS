from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class DispatchResult:
    mode: str            # "deep_link" now; "sent" for a real API provider later
    url: str | None
    detail: str


class WhatsAppProvider(ABC):
    """Outbound WhatsApp boundary. A WhatsApp Business API provider can implement this later."""

    @abstractmethod
    def dispatch(self, phone: str | None, message: str) -> DispatchResult: ...


class DeepLinkWhatsAppProvider(WhatsAppProvider):
    """Builds a wa.me link. Nothing is sent by VyapaarOS; the user taps Send in WhatsApp."""

    def dispatch(self, phone: str | None, message: str) -> DispatchResult:
        digits = "".join(ch for ch in (phone or "") if ch.isdigit())
        if len(digits) == 10:
            digits = "91" + digits  # default country code: India
        base = f"https://wa.me/{digits}" if digits else "https://wa.me/"
        return DispatchResult("deep_link", f"{base}?text={quote(message)}",
                              "Open WhatsApp to review and send")


def get_whatsapp_provider() -> WhatsAppProvider:
    return DeepLinkWhatsAppProvider()
