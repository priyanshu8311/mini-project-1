from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.database import get_db_session
from backend.src.domain.integrations.schemas import ShopifyWebhookProcessResult
from backend.src.domain.integrations.service import ShopifyService

webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


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
    Rejects invalid signatures with HTTP 401 Unauthorized before processing.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    return await ShopifyService.process_order_webhook(
        db=db,
        raw_body=raw_body,
        headers=headers,
        topic=topic,
    )
