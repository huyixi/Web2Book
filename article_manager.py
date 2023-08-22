from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import os
from concurrent.futures import ThreadPoolExecutor
import re
import yaml
import itertools
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Utility:
    
    @staticmethod
    def generate_filename_from_url(url, extension):
        return hashlib.md5(url.encode()).hexdigest() + "." + extension
    
    @staticmethod
    def ensure_directory_exists(directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def write_to_file(file_path, content):
        """Write content to the specified file path."""
        directory = os.path.dirname(file_path)
        Utility.ensure_directory_exists(directory)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def log_error_and_continue(message, error, url):
        """Log the error and continue the execution."""
        logger.error(f"{message} for {url}. Error: {error}. Continuing...")
    
    @staticmethod
    def extract_second_level_domain(url):
        parsed_uri = urlparse(url)
        domain = '{uri.netloc}'.format(uri=parsed_uri)
        parts = domain.split('.')
        if len(parts) < 2:
            return parts[0]
        else:
            return parts[-2]
    
    @staticmethod
    def get_cleaned_text(text):
        return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9.,?!]', '', text).strip().replace(' ', '-')
    
    @staticmethod
    def generate_image_save_path(url):
        path = urlparse(url).path
        img_url_extension = os.path.splitext(path)[1][1:]
        if not img_url_extension:
            img_url_extension = "jpg"
        img_filename = Utility.generate_filename_from_url(url, img_url_extension)
        return os.path.join('temp', img_filename)

class ImageHandler:
    def __init__(self, crawler, utility):
        self.crawler = crawler
        self.utility = utility

    def download_images(self, img_tags):
        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(self.download_image, img_tags)

    def download_image(self, img_tag, base_url):
        try:
            img_url = img_tag.get('src')
            if not img_url: 
                return
            absolute_img_url = urljoin(base_url, img_url)
            img_save_path = self.utility.generate_image_save_path(absolute_img_url)
        
            if self.crawler.fetch_image(absolute_img_url, img_save_path):
                img_tag['src'] = img_save_path
        except Exception as e:
            logger.error(f"Failed to fetch_image. Error: {e}")


class TOCManager:
    def __init__(self, crawler, utility):
        self.crawler = crawler
        self.utility = utility
        self.toc_list = []

    def _generate_filename_from_url(self, url, extension):
        return self.utility.generate_filename_from_url(url, extension)

    def get_toc(self, target_url, link_selector, next_page_selector=None):
        while target_url:
            logger.info(f"Crawling TOC from {target_url}...")
            html = self.crawler.fetch(target_url)
            if not html:
                logger.error(f"Failed to fetch {target_url}. Skipping...")
                continue
            soup = BeautifulSoup(html, 'html.parser')
            link_tags = soup.select(link_selector)
            for link_tag in link_tags:
                if 'href' in link_tag.attrs:
                    rel_url = link_tag['href']
                    chapter_url = urljoin(target_url, rel_url).strip()
                    chapter_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9.,?!]', '', link_tag.text).strip().replace(' ', '-')
                    filename = self._generate_filename_from_url(chapter_url, 'html')
                    self.toc_list.append({"title": chapter_title, "url": chapter_url, "filename": filename})
            if next_page_selector:
                next_page = soup.select_one(next_page_selector)
                if next_page and 'href' in next_page.attrs: 
                    target_url = urljoin(target_url, next_page['href'])
                else:
                    target_url = None
            else:
                break
        return self.toc_list

    def save_toc_to_file(self, base_dir='temp'):
        filepath = os.path.join(base_dir, "toc.yaml")
        os.makedirs(base_dir, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(self.toc_list, f, allow_unicode=True)
        logger.info(f"TOC saved to {filepath}")
        return filepath

class ArticleDownloader:
    
    def __init__(self, crawler, utility):
        self.crawler = crawler
        self.utility = utility

    def resolve_url(self, base_url, img_rel_url):
        if img_rel_url.startswith("//"):
            scheme = urlparse(base_url).scheme
            img_abs_url = f"{scheme}:{img_rel_url}"
        else:
            img_abs_url = urljoin(base_url, img_rel_url)
        return img_abs_url.strip()

    
    def fetch_article(self, url, title_selector, content_selector):
        logger.info(f"Fetching article from {url}...")
        html = self.crawler.fetch(url)
        if not html:
            logger.error(f"Failed to fetch article content from {url}. Skipping...")
            return None

        soup = BeautifulSoup(html, 'html.parser')
        title = soup.select_one(title_selector)
        if not title:
            logger.error(f"Failed to fetch article title from {url}. Skipping...")
            return None
        title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9.,?!]', '', title.text).strip().replace(' ', '-')


        # Download and update image paths
        for img_tag in soup.find_all('img'):
            try:
                img_rel_url = img_tag.get('src')
                if not img_rel_url:
                    logger.warning(f"Image tag without src found in {url}. Skipping...")
                else:
                    img_abs_url = self.resolve_url(url, img_rel_url)
                    img_save_path = self.utility.generate_image_save_path(img_abs_url)
                    if self.crawler.fetch_image(img_abs_url, img_save_path):
                        img_tag['src'] = img_save_path
                    else:
                        img_tag.decompose()
            except Exception as e:
                logger.error(f"Failed to save image. Error: {e}")

        content_element = soup.select_one(content_selector) or "no content"
        if content_element:
            content = content_element.prettify()
        else:
            logger.error(f"Failed to fetch article content from {url}. Skipping...")
            return None

        return {"title": title, "content": content,"url": url}
            

    def save_article(self, article_data, base_dir="temp"):
        file_name = self.utility.generate_filename_from_url(article_data["url"], 'html')
        file_path = os.path.join(base_dir, file_name)
        os.makedirs(base_dir, exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(article_data["content"])
            logger.info(f"Article saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save article to {file_path}. Error: {e}")

    def download_and_save(self, url, title_selector, content_selector, base_dir="temp"):
        try:
            article_data = self.fetch_article(url, title_selector, content_selector)
            if article_data:
                logger.info(f"Article data fetched from {url}. Saving to file...")
                self.save_article(article_data, base_dir)
            else:
                logger.error(f"Failed to fetch article data from {url}. Skipping...")
        except Exception as e:
            error_message = f"Error occurred while downloading and saving article from {url}. Error: {e}"
            logger.error(error_message)
            return error_message

class ArticleManager:
    def __init__(self, toc_manager, article_downloader):
        self.toc_manager = toc_manager
        self.article_downloader = article_downloader
    
    def generate_and_save_toc(self, target_url, link_selector, next_page_selector=None, base_dir='temp'):
        """
        Generate the table of contents (TOC) and save it to a YAML file.
        """
        toc = self.toc_manager.get_toc(target_url, link_selector, next_page_selector)
        toc_filepath = os.path.join(base_dir, "toc.yaml")
        os.makedirs(base_dir, exist_ok=True)
        with open(toc_filepath, 'w', encoding='utf-8') as f:
            yaml.dump(toc, f, allow_unicode=True)
        logger.info(f"TOC saved to {toc_filepath}")
        return toc

    def download_articles(self, toc, title_selector, content_selector, base_dir='temp'):
        """
        Download articles using the table of contents (TOC).
        """
        logger.info(f"Starting to download articles... Total articles: {len(toc)}")
        urls = [chapter['url'] for chapter in toc]
        if not urls:
            logger.warning("No URLs found in TOC. Skipping article download.")
            return

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(self.article_downloader.download_and_save, urls, 
                        itertools.repeat(title_selector), itertools.repeat(content_selector), 
                        itertools.repeat(base_dir))
        # Check if any exceptions occurred in the threads
        for result in results:
            if result:
                logger.error(f"Error occurred while downloading an article: {result}")