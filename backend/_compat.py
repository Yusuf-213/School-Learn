"""
Standard-library compat layer replacing the private `emergentintegrations` package.

Provides the same public surface (LlmChat, UserMessage, ImageContent, StripeCheckout,
CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse) using only
PyPI-standard packages: `openai` (talking to the Emergent OpenAI-compatible LLM proxy)
and `stripe`.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional

import stripe
from openai import AsyncOpenAI
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- LLM

_EMERGENT_LLM_BASE = os.getenv(
    "INTEGRATION_PROXY_URL",
    "https://integrations.emergentagent.com",
).rstrip("/") + "/llm/v1"


class FileContent:
    def __init__(self, content_type: str, file_content_base64: str) -> None:
        self.content_type = content_type
        self.file_content_base64 = file_content_base64


class ImageContent(FileContent):
    def __init__(self, image_base64: str) -> None:
        super().__init__("image", image_base64)

    @staticmethod
    def get_mime_type(b64: str) -> str:
        if b64.startswith("iVBORw0KGgo"):
            return "image/png"
        if b64.startswith("/9j/"):
            return "image/jpeg"
        if b64.startswith("R0lGOD"):
            return "image/gif"
        if b64.startswith("UklGR"):
            return "image/webp"
        return "image/png"


class UserMessage:
    def __init__(self, text: Optional[str] = None, file_contents: Optional[List[FileContent]] = None) -> None:
        self.text = text
        self.file_contents = file_contents or []


class ChatError(Exception):
    pass


class LlmChat:
    """
    Minimal drop-in replacement. Uses AsyncOpenAI with base_url pointed at
    Emergent's OpenAI-compatible LLM proxy — the same endpoint the original
    package used under the hood when it detected an `sk-emergent-…` key.

    Keeps a per-instance message history (in-memory only; server.py already
    treats it that way).
    """

    def __init__(self, api_key: str, session_id: str, system_message: str) -> None:
        self.api_key = api_key
        self.session_id = session_id
        self.provider = "openai"
        self.model = "gpt-4o"
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": system_message}]
        self._client = AsyncOpenAI(api_key=api_key, base_url=_EMERGENT_LLM_BASE)

    def with_model(self, provider: str, model: str) -> "LlmChat":
        self.provider = provider
        # Emergent proxy accepts bare model names (e.g. "claude-sonnet-4-5-20250929")
        # for anthropic/openai, and "gemini/<model>" for gemini.
        self.model = f"gemini/{model}" if provider == "gemini" else model
        return self

    def _serialise_user(self, msg: UserMessage) -> Dict[str, Any]:
        if not msg.file_contents:
            return {"role": "user", "content": msg.text or ""}
        content: List[Dict[str, Any]] = []
        if msg.text:
            content.append({"type": "text", "text": msg.text})
        for fc in msg.file_contents:
            if fc.content_type == "image":
                mime = ImageContent.get_mime_type(fc.file_content_base64)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{fc.file_content_base64}"},
                })
        return {"role": "user", "content": content}

    async def send_message(self, user_message: UserMessage) -> str:
        self.messages.append(self._serialise_user(user_message))
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=self.messages,
            )
            text = (resp.choices[0].message.content or "") if resp.choices else ""
            self.messages.append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            raise ChatError(f"Failed to generate chat completion: {e}") from e


# --------------------------------------------------------------------------- Stripe


class CheckoutSessionRequest(BaseModel):
    amount: Optional[float] = None
    currency: str = "usd"
    stripe_price_id: Optional[str] = None
    quantity: int = 1
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    payment_methods: Optional[List[str]] = Field(default_factory=lambda: ["card"])


class CheckoutSessionResponse(BaseModel):
    url: str
    session_id: str


class CheckoutStatusResponse(BaseModel):
    status: str
    payment_status: str
    amount_total: int
    currency: str
    metadata: Dict[str, str]


class WebhookEventResponse(BaseModel):
    event_type: str
    event_id: str
    session_id: Optional[str] = None
    payment_status: Optional[str] = None
    metadata: Dict[str, str]


class CheckoutError(Exception):
    pass


class StripeCheckout:
    """
    Drop-in replacement using the stock `stripe` PyPI package.
    """

    def __init__(self, api_key: str, webhook_secret: Optional[str] = None, webhook_url: Optional[str] = None) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.webhook_url = webhook_url
        stripe.api_key = api_key
        if api_key and "sk_test_emergent" in api_key:
            stripe.api_base = "https://integrations.emergentagent.com/stripe"

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> CheckoutSessionResponse:
        try:
            if req.amount is not None:
                line_items = [{
                    "price_data": {
                        "currency": req.currency,
                        "product_data": {"name": "Payment"},
                        "unit_amount": int(req.amount * 100),
                    },
                    "quantity": 1,
                }]
            else:
                line_items = [{"price": req.stripe_price_id, "quantity": req.quantity}]

            metadata = dict(req.metadata or {})
            if self.webhook_url:
                metadata["webhook_url"] = self.webhook_url

            session = stripe.checkout.Session.create(
                payment_method_types=req.payment_methods or ["card"],
                line_items=line_items,
                mode="payment",
                success_url=req.success_url,
                cancel_url=req.cancel_url,
                metadata=metadata,
            )
            return CheckoutSessionResponse(url=session.url, session_id=session.id)
        except stripe.error.StripeError as e:
            raise CheckoutError(f"Failed to create checkout session: {e}") from e
        except Exception as e:
            raise CheckoutError(f"Unexpected error creating checkout session: {e}") from e

    async def get_checkout_status(self, checkout_session_id: str) -> CheckoutStatusResponse:
        try:
            s = stripe.checkout.Session.retrieve(checkout_session_id)
            return CheckoutStatusResponse(
                status=s.status,
                payment_status=s.payment_status,
                amount_total=s.amount_total or 0,
                currency=s.currency or "",
                metadata=dict(s.metadata or {}),
            )
        except stripe.error.StripeError as e:
            raise CheckoutError(f"Failed to retrieve session status: {e}") from e
        except Exception as e:
            raise CheckoutError(f"Unexpected error retrieving session status: {e}") from e

    async def handle_webhook(self, payload: bytes, signature: Optional[str] = None) -> WebhookEventResponse:
        try:
            if self.webhook_secret and signature:
                event = stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
                event = event if isinstance(event, dict) else event.to_dict()
            else:
                event = json.loads(payload.decode("utf-8"))

            etype = event["type"]
            eid = event["id"]
            obj = event.get("data", {}).get("object", {}) or {}
            metadata = dict(obj.get("metadata") or {})
            session_id: Optional[str] = None
            payment_status: Optional[str] = None

            if etype in {"checkout.session.completed", "checkout.session.expired"}:
                session_id = obj.get("id")
                payment_status = obj.get("payment_status")
            elif etype == "payment_intent.succeeded":
                session_id = (obj.get("metadata") or {}).get("checkout_session_id")
                payment_status = "paid"
            elif etype == "payment_intent.payment_failed":
                session_id = (obj.get("metadata") or {}).get("checkout_session_id")
                payment_status = "failed"

            return WebhookEventResponse(
                event_type=etype,
                event_id=eid,
                session_id=session_id,
                payment_status=payment_status,
                metadata=metadata,
            )
        except json.JSONDecodeError as e:
            raise CheckoutError(f"Invalid JSON payload: {e}") from e
        except Exception as e:
            raise CheckoutError(f"Unexpected error processing webhook: {e}") from e
