import requests
from fake_useragent import UserAgent

class Crawler:
    def __init__(self, proxy_pool_url=None):
        self.ua = UserAgent()
        self.proxy_pool_url = proxy_pool_url

    def get_proxy(self):
        if self.proxy_pool_url:
            return requests.get(self.proxy_pool_url).text.strip()
        else:
            return requests.get('http://127.0.0.1:5555/random').text.strip()

    def fetch(self, url, max_retries=3):
        headers = {'User-Agent': self.ua.random}
    
        for _ in range(max_retries):
            proxy = self.get_proxy()
            proxies = {'http': 'http://' + proxy}
                    
            print(f"Crawling:{url} proxy:http://{proxy}...")

            try:
                res = requests.get(url, headers=headers, proxies=proxies, timeout=10)
                if res.status_code == 200:
                    return res.text
                else:
                    print(f"Failed to fetch with status code {res.status_code}: {url}")
                    raise Exception(f"Failed with status code {res.status_code}")
            except requests.RequestException as e:
                print(f"Request failed with proxy {proxy}. Error: {e}")
                raise e 

        print(f"Failed to fetch after {max_retries} retries: {url}")
        raise Exception(f"Failed to fetch after {max_retries} retries")

    def download_image(self, url, save_path, max_retries=3):
            headers = {'User-Agent': self.ua.random}

            for _ in range(max_retries):
                proxy = self.get_proxy()
                proxies = {'http': 'http://' + proxy}

                print(f"Downloading:{url} using proxy:http://{proxy}...")

                try:
                    res = requests.get(url, headers=headers, proxies=proxies, timeout=10, stream=True)
                    res.raise_for_status()

                    with open(save_path, 'wb') as file:
                        for chunk in res.iter_content(chunk_size=8192):
                            file.write(chunk)

                    print(f"Image saved to {save_path}")
                    return True

                except requests.RequestException as e:
                    print(f"Request failed with proxy {proxy}. Error: {e}")

            print(f"Failed to download after {max_retries} retries: {url}")
            return False