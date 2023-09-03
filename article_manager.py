from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import os
from concurrent.futures import ThreadPoolExecutor
import re
import yaml
import itertools
import hashlib
import logging
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.ERROR)
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
    def write_to_file(file_path, content,encoding):
        """Write content to the specified file path."""
        directory = os.path.dirname(file_path)
        Utility.ensure_directory_exists(directory)
        with open(file_path, 'w', encoding=encoding) as f:
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
        return os.path.join('tmp',img_filename)

class ImageHandler:
    def __init__(self, crawler, utility, max_retries=3):
        self.crawler = crawler
        self.utility = utility
        self.max_retries = max_retries

    def download_images(self, img_tags):
        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(self.download_image, img_tags)

    def download_image(self, img_tag, base_url):
        try:
            img_url = img_tag.get('src')
            if not img_url: 
                logger.warning(f"Image tag without src attribute found. Skipping...")
                return
            absolute_img_url = urljoin(base_url, img_url)
            img_save_path = os.path.join(self.utility.generate_image_save_path(absolute_img_url))
        
            for attempt in range(self.max_retries):
                try:
                    if self.crawler.fetch_image(absolute_img_url, img_save_path):
                        logger.info(f"Image downloaded from {absolute_img_url}")
                        img_filename = os.path.basename(img_save_path)
                        img_tag['src'] = img_filename
                        return img_save_path
                    else:
                        logger.warning(f"Failed to fetch_image. Retrying... ({attempt + 1}/{self.max_retries})")
                except Exception as e:
                    logger.error(f"Failed to fetch_image. Error: {e}. Retrying... ({attempt + 1}/{self.max_retries})")
                    if attempt == self.max_retries - 1:
                        logger.error(f"Failed to download image from {absolute_img_url} after {self.max_retries} attempts.")
        except Exception as e:
            logger.error(f"Failed to fetch_image. Error: {e}")

    def handle_images_in_content(self, content, base_url):
        try:
            soup = BeautifulSoup(content, 'html.parser')
            for img_tag in soup.find_all('img'):
                self.download_image(img_tag, base_url)
            return soup.prettify()
        except Exception as e:
            logger.error(f"Failed to download image in content. Error: {e}")
            
    def generate_book_cover(self, title, size=(1600, 2560), bg_color="white"):
        # Create a figure and axis with desired size
        fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    
        # Set the background color
        ax.set_facecolor(bg_color)
        fig.patch.set_facecolor(bg_color)
    
        # Remove axis
        ax.axis('off')
    
        # Add title text to the center of the figure
        plt.text(0.5, 0.5, title, color=(0, 0, 0), fontsize=150, ha='center', va='center', transform=ax.transAxes)
    
        # Ensure the output directory exists
        try:
            if not os.path.exists("tmp"):
                os.mkdir("tmp")
            plt.savefig("tmp/cover.jpg", bbox_inches="tight", pad_inches=0, dpi=100)
            plt.close()
        except Exception as e:
            logger.error(f"Failed to generate book cover. Error: {e}")

class TOCManager:
    def __init__(self, crawler, utility):
        self.crawler = crawler
        self.utility = utility
        self.toc_list = []

    def _generate_filename_from_url(self, url, extension):
        return self.utility.generate_filename_from_url(url, extension)

    def get_toc(self, target_url, link_selector, next_page_selector=None):
        while target_url:
            logger.info(f"Crawling TOC from {target_url}")
            html = self.crawler.fetch(target_url)
            content = html["content"]
            encoding = html["encoding"]
            self.save_toc_html_to_file(content,encoding)
            if not html:
                logger.error(f"Failed to fetch {target_url}. Skipping...")
                continue
            soup = BeautifulSoup(content, 'html.parser')
            link_tags = soup.select(link_selector)
            for link_tag in link_tags:
                if 'href' in link_tag.attrs:
                    rel_url = link_tag['href']
                    chapter_url = urljoin(target_url, rel_url).strip()
                    chapter_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9.,?!_-]', '', link_tag.text.strip().replace(' ', '_'))
                    filename = self._generate_filename_from_url(chapter_url, 'html')
                    self.toc_list.append({"chapter_title": chapter_title, "url": chapter_url, "filename": filename})
            if next_page_selector:
                next_page = soup.select_one(next_page_selector)
                if next_page and 'href' in next_page.attrs: 
                    target_url = urljoin(target_url, next_page['href'])
                else:
                    target_url = None
            else:
                break
        return {"toc":self.toc_list, "encoding": encoding}
    
    def save_toc_html_to_file(self, html, encoding, base_dir='tmp'):
        filepath = os.path.join(base_dir, "toc.html")
        os.makedirs(base_dir, exist_ok=True)
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(html)
        logger.info(f"TOC HTML saved to {filepath}")

    def save_toc_to_file(self,encoding, base_dir='tmp'):
        filepath = os.path.join(base_dir, "toc.yaml")
        os.makedirs(base_dir, exist_ok=True)
        with open(filepath, 'w', encoding=encoding) as f:
            yaml.dump(self.toc_list, f, allow_unicode=True)
        logger.info(f"TOC saved to {filepath}")
        return filepath

class ArticleDownloader:
    
    def __init__(self, crawler, utility, image_handler):
        self.crawler = crawler
        self.utility = utility
        self.image_handler = image_handler

    def resolve_url(self, base_url, img_rel_url):
        if img_rel_url.startswith("//"):
            scheme = urlparse(base_url).scheme
            img_abs_url = f"{scheme}:{img_rel_url}"
        else:
            img_abs_url = urljoin(base_url, img_rel_url)
        return img_abs_url.strip()

    def fetch_article(self, url, article_selector, remove_selectors):
        logger.info(f"Fetching article from {url}...")
        html = self.crawler.fetch(url)
        content = html["content"]
        encoding = html["encoding"]
        if not html:
            logger.error(f"Failed to fetch article content from {url}. Skipping...")
            return None

        # Check if the selector is valid
        if not article_selector or not isinstance(article_selector, str) or len(article_selector.strip()) == 0:
            error_message = f"Invalid or empty CSS selector provided for {url}. Please provide a valid selector."
            logger.error(error_message)
            return None

        soup = BeautifulSoup(content, 'html.parser')

        if remove_selectors:
            try:
                for selector in remove_selectors:
                    if selector:
                        for elem in soup.select(selector.strip()):
                            elem.extract()
            except Exception as e:
                logger.error(f"Error removing elements with selector '{selector}': {e}")
        
        article_element = soup.select_one(article_selector)
        if article_element:
            article = self.image_handler.handle_images_in_content(article_element.prettify(), url)
        else:
            article = content
            logger.error(f"Failed to fetch article content from {url}.")
            return None

        return {"content": article, "encoding": encoding}

    def save_article(self, url, content ,encoding, base_dir="tmp"):
        file_name = self.utility.generate_filename_from_url(url, 'html')
        file_path = os.path.join(base_dir, file_name)
        os.makedirs(base_dir, exist_ok=True)
        try:
            with open(file_path, 'w', encoding=encoding) as file:
                file.write(content)
            logger.info(f"Article saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save article to {file_path}. Error: {e}")

    def download_and_save(self, url, article_selector, remove_selectors, base_dir="tmp"):
        try:
            html = self.fetch_article(url, article_selector, remove_selectors)
            if html:
                logger.info(f"Article data fetched from {url}. Saving to file...")
                self.save_article(url, html["content"],html["encoding"], base_dir)
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
    
    def generate_and_save_toc(self, target_url, link_selector, next_page_selector=None, base_dir='tmp'):
        toc_data = self.toc_manager.get_toc(target_url, link_selector, next_page_selector)
        toc = toc_data["toc"]
        toc_encoding = toc_data["encoding"]
        toc_filepath = os.path.join(base_dir, "toc.yaml")
        os.makedirs(base_dir, exist_ok=True)
        with open(toc_filepath, 'w', encoding=toc_encoding) as f:
            yaml.dump(toc, f, allow_unicode=True)
        logger.info(f"TOC saved to {toc_filepath}")
        return toc

    def download_articles(self, toc, article_selector, base_dir='tmp'):
        logger.info(f"Starting to download articles... Total articles: {len(toc)}")
        urls = [chapter['url'] for chapter in toc]
        if not urls:
            logger.warning("No URLs found in TOC. Skipping article download.")
            return

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(self.article_downloader.download_and_save, urls,
                        itertools.repeat(article_selector), 
                        itertools.repeat(base_dir))
        # Check if any exceptions occurred in the threads
        for result in results:
            if result:
                logger.error(f"Error occurred while downloading an article: {result}")