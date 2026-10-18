import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ShopifyAPIError(Exception):
    """Base exception for Shopify API communication failures."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class ShopifyAuthError(ShopifyAPIError):
    """Authentication or authorization failure with Shopify Admin API."""


class ShopifyNotFoundError(ShopifyAPIError):
    """Requested Shopify resource or shop domain was not found."""


class ShopifyRateLimitError(ShopifyAPIError):
    """Shopify API rate limit exceeded (HTTP 429)."""

    def __init__(self, message: str, retry_after: float = 2.0):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ShopifyValidationError(ShopifyAPIError):
    """Shopify rejected request payload validation (HTTP 422)."""


class ShopifyClient:
    """Production-grade asynchronous client for Shopify Admin REST API.

    Features:
    - Masked credential logging (least-privilege visibility)
    - Automatic exponential backoff on transient network and 5xx errors
    - Rate limit (HTTP 429) detection and Retry-After inspection
    - Strict connection, read, and write timeouts
    """

    def __init__(
        self,
        shop_domain: str,
        access_token: str,
        api_version: str = "2024-01",
        timeout: float = 10.0,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
    ):
        self.shop_domain = shop_domain.strip().lower()
        self.access_token = access_token
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.base_url = f"https://{self.shop_domain}/admin/api/{self.api_version}"

    @property
    def masked_token(self) -> str:
        """Return safe representation of token for logging."""
        if not self.access_token or len(self.access_token) <= 8:
            return "********"
        return f"{self.access_token[:4]}...{self.access_token[-4:]}"

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SmartInventoryDemandForecasting/1.0",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        is_idempotent: bool = True,
    ) -> dict[str, Any]:
        """Execute HTTP request against Shopify Admin API with resiliency and retry logic."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        attempt = 0
        while True:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(
                        "Shopify API %s %s (Attempt %d/%d, Token: %s)",
                        method,
                        endpoint,
                        attempt,
                        self.max_retries + 1,
                        self.masked_token,
                    )
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_data,
                    )

                status = response.status_code

                # Success
                if 200 <= status < 300:
                    return response.json() if response.content else {}

                # 401/403: Credentials invalid or missing scopes (never retry)
                if status in (401, 403):
                    logger.warning(
                        "Shopify authentication failed for %s: HTTP %d",
                        self.shop_domain,
                        status,
                    )
                    raise ShopifyAuthError(
                        f"Shopify authentication failed (HTTP {status}). Verify API access token.",
                        status_code=status,
                    )

                # 404: Not found
                if status == 404:
                    raise ShopifyNotFoundError(
                        f"Shopify resource not found at {endpoint} (HTTP 404).",
                        status_code=404,
                    )

                # 422: Unprocessable Entity / Validation failure
                if status == 422:
                    error_data = response.json() if response.content else {}
                    raise ShopifyValidationError(
                        f"Shopify payload validation failed: {error_data}",
                        status_code=422,
                        details=error_data,
                    )

                # 429: Leaky bucket rate limit reached
                if status == 429:
                    retry_header = response.headers.get("Retry-After")
                    try:
                        retry_after = float(retry_header) if retry_header else 2.0
                    except ValueError:
                        retry_after = 2.0

                    logger.warning(
                        "Shopify rate limit hit for %s. Retry-After: %.2fs",
                        self.shop_domain,
                        retry_after,
                    )

                    if attempt <= self.max_retries and is_idempotent:
                        await asyncio.sleep(retry_after)
                        continue

                    raise ShopifyRateLimitError(
                        f"Shopify API rate limit exceeded. Retry after {retry_after}s.",
                        retry_after=retry_after,
                    )

                # 5xx Server Errors (Transient)
                if status >= 500:
                    logger.warning(
                        "Shopify upstream server error %d on %s",
                        status,
                        endpoint,
                    )
                    if attempt <= self.max_retries and is_idempotent:
                        backoff = self.base_backoff_seconds * (2 ** (attempt - 1))
                        await asyncio.sleep(backoff)
                        continue

                    raise ShopifyAPIError(
                        f"Shopify server error (HTTP {status}). Please try again later.",
                        status_code=status,
                    )

                # Unhandled HTTP error
                raise ShopifyAPIError(
                    f"Unexpected Shopify API response: HTTP {status}",
                    status_code=status,
                )

            except (httpx.TimeoutException, httpx.NetworkError) as err:
                logger.warning(
                    "Network error communicating with Shopify %s: %s (Attempt %d)",
                    self.shop_domain,
                    str(err),
                    attempt,
                )
                if attempt <= self.max_retries and is_idempotent:
                    backoff = self.base_backoff_seconds * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)
                    continue

                raise ShopifyAPIError(
                    f"Network or timeout connecting to Shopify: {err}",
                ) from err

    async def get_shop(self) -> dict[str, Any]:
        """Fetch shop metadata to verify API token validity and retrieve store details."""
        data = await self._request("GET", "shop.json", is_idempotent=True)
        return data.get("shop", {})

    async def get_locations(self) -> list[dict[str, Any]]:
        """Fetch active locations configured in the Shopify merchant store."""
        data = await self._request("GET", "locations.json", is_idempotent=True)
        return data.get("locations", [])

    async def set_inventory_level(
        self,
        location_id: int | str,
        inventory_item_id: int | str,
        available: int,
    ) -> dict[str, Any]:
        """Set on-hand available inventory for a specific item at a location.

        Operation is idempotent in Shopify REST API (POST /inventory_levels/set.json).
        """
        payload = {
            "location_id": int(location_id),
            "inventory_item_id": int(inventory_item_id),
            "available": int(available),
        }
        data = await self._request(
            "POST",
            "inventory_levels/set.json",
            json_data=payload,
            is_idempotent=True,
        )
        return data.get("inventory_level", {})

    async def get_inventory_levels(
        self,
        inventory_item_ids: list[int | str],
        location_ids: list[int | str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch current inventory levels from Shopify."""
        params: dict[str, Any] = {
            "inventory_item_ids": ",".join(str(i) for i in inventory_item_ids)
        }
        if location_ids:
            params["location_ids"] = ",".join(str(loc) for loc in location_ids)

        data = await self._request(
            "GET",
            "inventory_levels.json",
            params=params,
            is_idempotent=True,
        )
        return data.get("inventory_levels", [])
