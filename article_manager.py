from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import os
import datetime
from concurrent.futures import ThreadPoolExecutor
import re
import yaml
import itertools
import hashlib

class ArticleManager:
    def __init__(self, crawler):
        self.crawler = crawler
        self.toc_list = []
    
    def _generate_filename_from_url(self, url, extension):
        return hashlib.md5(url.encode()).hexdigest() + "." + extension

    def _get_domain_name(self,url):
        parsed_uri = urlparse(url)
        domain = '{uri.netloc}'.format(uri=parsed_uri)
        return domain

    def get_toc(self, target_url, link_selector, next_page_selector=None):
        original_url = target_url
        # get title and link
        while target_url:
            print(f"Crawling toc from {target_url}...")
            html = self.crawler.fetch(target_url)
            if not html:
                print(f"Failed to fetch {target_url}")
                return None
            soup = BeautifulSoup(html, 'html.parser')
            link_tags = soup.select(link_selector)
            for link_tag in link_tags:
                if 'href' in link_tag.attrs:
                    rel_url = link_tag['href']
                    chapter_url = urljoin(target_url, rel_url).strip()
                    chapter_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9.,?!]', '', link_tag.text).strip().replace(' ', '-')
                    filename = self._generate_filename_from_url(chapter_url, 'html')
                    self.toc_list.append({"title": chapter_title, "url": chapter_url, "filename": filename})

            # Look for the next page link
            if next_page_selector:
                next_page = soup.select_one(next_page_selector)
                if next_page:
                    target_url = urljoin(target_url, next_page['href'])
                else:
                    target_url = None

        # Save the toc as a yaml file and return it
        dic_path = self._get_domain_name(original_url)
        toc_filename = self._get_domain_name(original_url)
        filepath = os.path.join(dic_path, toc_filename + '.yaml')
        if not os.path.exists(dic_path):
            os.makedirs(dic_path)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(self.toc_list, f, allow_unicode=True)
        return self.toc_list

    def get_articles(self,title_selector,content_selector):
        urls = [chapter['url'] for chapter in self.toc_list]
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(self._crawl_and_save, urls, itertools.repeat(title_selector), itertools.repeat(content_selector))
    
    def _crawl_and_save(self, url,title_selector,content_selector):
        article_data = self._get_article_data(url,title_selector,content_selector)
        if not article_data:
            print(f"Failed to fetch article data from {url}")
            return
    
        content = article_data['content']

        file_name = self._generate_filename_from_url(url,'html')
        dic_path = self._get_domain_name(url)
        file_path = os.path.join(dic_path, file_name)
        print(f"file_name:{file_name},file_path:{file_path}")
        self._write_to_file(file_path, content)

    def _write_to_file(self, file_path, content):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _get_article_data(self, url,title_selector,content_selector):
        html = self.crawler.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        raw_title = soup.select_one(title_selector)
        if raw_title:
            cleaned_title = " ".join(raw_title.text.split())
            title = cleaned_title.replace(' ', '-')
            title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9.,?!]', '', title).strip() 
        content_element = soup.select_one(content_selector)

        for img_tag in soup.find_all('img'):
            img_url = img_tag['src']
            img_url_extension = img_url.split('.')[-1]
            img_filename = self._generate_filename_from_url(img_url, img_url_extension)
            img_save_path = os.path.join(self._get_domain_name(url), img_filename)
        
            if not self.crawler.download_image(img_url, img_save_path):
                img_tag.decompose()
            else:
                img_tag['src'] = img_save_path
        
        content = content_element.prettify() or "no content"
        return {"title": title, "content": content}