import logging
from scrapy.http import HtmlResponse
from scrapy.exceptions import IgnoreRequest
from curl_cffi.requests import AsyncSession, RequestsError

logger = logging.getLogger(__name__)

class CloudflareBypassMiddleware:
    """
    Downloader middleware that intercepts requests requiring Cloudflare bypass
    and routes them through curl_cffi to spoof browser TLS/JA3/JA4 fingerprints.
    """

    async def process_request(self, request, spider):
        if not request.meta.get('bypass_cloudflare'):
            # Return None to let Scrapy's default downloader process this request
            return None

        logger.info(f"Bypassing Cloudflare for URL: {request.url} using curl_cffi...")

        # Parse Scrapy headers to dict for curl_cffi compatibility
        headers = {}
        for key, value_list in request.headers.items():
            # Scrapy headers keys and values are bytes
            decoded_key = key.decode('utf-8') if isinstance(key, bytes) else key
            decoded_value = value_list[0].decode('utf-8') if isinstance(value_list[0], bytes) else value_list[0]
            headers[decoded_key] = decoded_value

        # Use curl_cffi's AsyncSession to make a non-blocking HTTP request
        try:
            async with AsyncSession() as session:
                # Impersonate a modern Chrome browser to bypass TLS fingerprint blocks
                response = await session.request(
                    method=request.method,
                    url=request.url,
                    headers=headers,
                    data=request.body,
                    impersonate="chrome110",
                    allow_redirects=True,
                    timeout=30
                )

                # Return the response as a Scrapy HtmlResponse. 
                # Returning a Response object bypasses subsequent downloader middlewares
                # and sends the response directly to the spider's parse method.
                return HtmlResponse(
                    url=response.url,
                    status=response.status_code,
                    headers=dict(response.headers),
                    body=response.content,
                    encoding='utf-8',
                    request=request
                )

        except RequestsError as e:
            logger.error(f"curl_cffi request failed for {request.url}: {str(e)}")
            # Fail the request and let Scrapy handle retries or errors
            raise IgnoreRequest(f"Failed to bypass Cloudflare via curl_cffi: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in CloudflareBypassMiddleware for {request.url}: {str(e)}")
            raise IgnoreRequest(f"Unexpected middleware error: {str(e)}")
