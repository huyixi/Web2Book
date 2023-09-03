import requests
from fake_useragent import UserAgent
import logging
import time
import inquirer

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

    def _make_request(self, method, url, timeout=(5, 15), **kwargs):
        headers = kwargs.pop('headers', {})
        headers['User-Agent'] = self.ua.random
        proxies = {}

        if self.proxy_pool_url:
            proxy_address = self._get_proxy()
            proxies = {'http': 'http://' + proxy_address}
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, headers=headers, proxies=proxies, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
            
            except requests.Timeout as e:
                new_timeout = self.handle_timeout(url, timeout)
                if new_timeout:
                    timeout = new_timeout
                else:
                    self.failed_requests.append((url, str(e)))
                    logger.error(f"Request failed for URL: {url} with error: {e}")

            except requests.RequestException as e:
                if attempt == self.max_retries:
                    self.failed_requests.append((url, str(e)))
                    logger.error(f"Request failed for URL: {url} with error: {e}")
                else:
                    wait_time = self._wait_time(attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)

    def handle_timeout(self, url, timeout):            
        questions = [
            inquirer.Text('new_timeout', message=f"Request for {url} timed out after {timeout[1]} seconds. Enter new timeout in seconds (or press Enter to skip):")
        ]
        answers = inquirer.prompt(questions)
        try:
            return (5, int(answers['new_timeout']))
        except (TypeError, ValueError):
            return None
            
    def fetch(self, url, **kwargs):
        response = self._make_request('GET', url, **kwargs)
        response.encoding = response.apparent_encoding or 'utf-8'
        return {"content":response.text, "encoding": response.encoding} if response else None

    def fetch_image(self, url, save_path, **kwargs):
        response = self._make_request('GET', url, stream=True, **kwargs)
        if response:
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            return True
        return False

    def print_failed_requests(self):
        if self.failed_requests:
            print("\nFailed Requests:")
            for url, error in self.failed_requests:
                print(f"URL: {url} - Error: {error}")