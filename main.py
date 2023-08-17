import inquirer
import validators
from crawler import Crawler
from article_manager import ArticleManager
from epub_generator import EpubGenerator

def validate_url(answers, url):
    if validators.url(url) or validators.url('http://' + url):
        return True
    return  False 

def get_valid_url(message):
    questions = [
        inquirer.Text('target_link', message=message, validate=validate_url)
    ]
    answers = inquirer.prompt(questions)
    url = answers['target_link']
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def get_link_selector(message):
    questions = [
            inquirer.Text('link_selector', message=message)
        ]
    answers = inquirer.prompt(questions)
    return answers['link_selector'] or "a"

def get_proxy_pool_url(message):
    questions = [
            inquirer.Text('proxy', message=message)
        ]
    answers = inquirer.prompt(questions)
    if answers and answers['proxy']:
        return answers['proxy']

def get_title_selector(message):
    questions = [
            inquirer.Text('title_selector', message=message)
        ]
    answers = inquirer.prompt(questions)
    return answers['title_selector'] or "h1"

def get_content_selector(message):
    questions = [
            inquirer.Text('content_selector', message=message)
        ]
    answers = inquirer.prompt(questions)
    return answers['content_selector'] or "main"

if __name__ == "__main__":
    target_url = get_valid_url("Enter the URL of the website to be crawled")
    link_selector = get_link_selector("Enter the CSS selector to find the links")
    proxy_pool_url = get_proxy_pool_url("Enter the URL of the proxy pool")
    crawler = Crawler(proxy_pool_url)
    article_manager = ArticleManager(crawler)
    toc_list = article_manager.get_toc(target_url, link_selector)
    base_dir = article_manager._get_domain_name(target_url)
    title_selector = get_title_selector("Enter the CSS selector to find the title")
    content_selector = get_content_selector("Enter the CSS selector to find the content")
    article_manager.get_articles(title_selector,content_selector)
    epub_generator = EpubGenerator(base_dir)
    epub_generator.generate_epub(toc_list)
