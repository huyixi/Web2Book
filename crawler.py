import requests
from fake_useragent import UserAgent
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Crawler:
    def __init__(self, proxy_pool_url=None, max_retries=3):
        self.ua = UserAgent()
        self.proxy_pool_url = proxy_pool_url
        self.max_retries = max_retries
        self.failed_requests = []
        self.session = requests.Session()

    def _get_proxy(self):
        if self.proxy_pool_url:
            return requests.get(self.proxy_pool_url).text.strip()
        return None

    def _wait_time(self, attempt, backoff_factor=2):
        return backoff_factor ** attempt

    def _make_request(self, method, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['User-Agent'] = self.ua.random
        proxies = {}

        if self.proxy_pool_url:
            proxy_address = self._get_proxy()
            proxies = {'http': 'http://' + proxy_address}
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, headers=headers, proxies=proxies, timeout=(5, 15), **kwargs)
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                if attempt == self.max_retries:
                    self.failed_requests.append((url, str(e)))
                    logger.error(f"Request failed for URL: {url} with error: {e}")
                else:
                    wait_time = self._wait_time(attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)

    def fetch(self, url, **kwargs):
        response = self._make_request('GET', url, **kwargs)
        return response.text if response else None

    def download_image(self, url, save_path, **kwargs):
        response = self._make_request('GET', url, stream=True, **kwargs)
        if response:
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

    def print_failed_requests(self):
        if self.failed_requests:
            print("\nFailed Requests:")
            for url, error in self.failed_requests:
                print(f"URL: {url} - Error: {error}")