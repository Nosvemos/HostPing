import logging
from scrapy.http import HtmlResponse
from scrapy.exceptions import IgnoreRequest
from twisted.internet.threads import deferToThread
from curl_cffi import requests as curl_requests
from curl_cffi.requests import RequestsError

logger = logging.getLogger(__name__)

class CloudflareBypassMiddleware:
    """
    Downloader middleware that intercepts requests requiring Cloudflare bypass
    and routes them through curl_cffi inside Twisted's threadpool to spoof
    browser TLS/JA3/JA4 fingerprints without blocking the main event loop.
    """

    def process_request(self, request, spider):
        if not request.meta.get('bypass_cloudflare'):
            # Return None to let Scrapy's default downloader process this request
            return None

        logger.info(f"Bypassing Cloudflare for URL: {request.url} using curl_cffi in background thread...")
        return deferToThread(self._download_with_curl, request)

    def _download_with_curl(self, request):
        # Parse Scrapy headers to dict for curl_cffi compatibility
        headers = {}
        for key, value_list in request.headers.items():
            decoded_key = key.decode('utf-8') if isinstance(key, bytes) else key
            decoded_value = value_list[0].decode('utf-8') if isinstance(value_list[0], bytes) else value_list[0]
            headers[decoded_key] = decoded_value

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Impersonate a modern Chrome browser to bypass TLS fingerprint blocks
                response = curl_requests.request(
                    method=request.method,
                    url=request.url,
                    headers=headers,
                    data=request.body,
                    impersonate="chrome110",
                    allow_redirects=True,
                    timeout=30
                )

                # Copy headers and remove encoding/length since curl_cffi automatically decompresses it
                resp_headers = dict(response.headers)
                for header_key in list(resp_headers.keys()):
                    if header_key.lower() in ('content-encoding', 'content-length'):
                        resp_headers.pop(header_key, None)

                # Return the response as a Scrapy HtmlResponse.
                return HtmlResponse(
                    url=response.url,
                    status=response.status_code,
                    headers=resp_headers,
                    body=response.content,
                    encoding='utf-8',
                    request=request
                )

            except RequestsError as e:
                logger.error(f"curl_cffi request failed for {request.url} (Attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise IgnoreRequest(f"Failed to bypass Cloudflare via curl_cffi after {max_retries} attempts: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error in CloudflareBypassMiddleware for {request.url} (Attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise IgnoreRequest(f"Unexpected middleware error: {str(e)}")
