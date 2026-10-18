from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.database import get_db_session
from backend.src.core.errors import ValidationException
from backend.src.domain.integrations.schemas import ShopifyWebhookProcessResult
from backend.src.domain.integrations.service import ShopifyService

webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

MAX_WEBHOOK_PAYLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


@webhooks_router.post(
    "/shopify/{topic:path}",
    response_model=ShopifyWebhookProcessResult,
    status_code=status.HTTP_200_OK,
    summary="Receive and verify Shopify real-time webhook events",
)
async def handle_shopify_webhook(
    topic: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ShopifyWebhookProcessResult:
    """Public webhook receiver endpoint for Shopify store events (e.g. orders/create).

    Enforces cryptographic HMAC-SHA256 signature verification via X-Shopify-Hmac-Sha256.
    Rejects oversized payloads (>2MB) to prevent denial-of-service memory exhaustion.
    Rejects invalid signatures with HTTP 401 Unauthorized before processing.
    """
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_WEBHOOK_PAYLOAD_BYTES:
                raise ValidationException(
                    "Webhook payload exceeds maximum allowable size (2MB).",
                    details=[{"field": "body", "issue": "PAYLOAD_TOO_LARGE"}],
                )
        except ValueError:
            pass

    raw_body = await request.body()
    if len(raw_body) > MAX_WEBHOOK_PAYLOAD_BYTES:
        raise ValidationException(
            "Webhook payload exceeds maximum allowable size (2MB).",
            details=[{"field": "body", "issue": "PAYLOAD_TOO_LARGE"}],
        )

    headers = dict(request.headers)

    return await ShopifyService.process_order_webhook(
        db=db,
        raw_body=raw_body,
        headers=headers,
        topic=topic,
    )
