import inquirer
import validators
from crawler import Crawler
from article_manager import ArticleManager, TOCManager, ArticleDownloader, Utility
from epub_generator import EpubGenerator


def get_input(message, default=None, validate=None):
    if validate:
        questions = [inquirer.Text('input', message=message, default=default, validate=validate)]
    else:
        questions = [inquirer.Text('input', message=message, default=default)]
    answers = inquirer.prompt(questions)
    return answers['input']

def ensure_url_scheme(url):
    if not url.startstwith(("https://","http://")):
        return 'https://' + url
    return url

def validate_url(answers, url):
    return True if validators.url(url) or validators.url('http://' + url) else None

def get_book_metadata():
    return {
        'book_title': get_input("Enter the title of the book"),
        'book_author': get_input("Enter the author of the book"),
        'book_language': get_input("Enter the language of the book (e.g., en for English)"),
        'book_identifier': get_input("Enter a unique identifier for the book (or press Enter to generate one)", default=None),
        'output_filename': get_input("Enter the output filename (without extension)", default="output")
    }

if __name__ == "__main__":
    utility = Utility()
    target_url = get_input("Enter the URL of the website to be crawled",default="https://blog.samaltman.com/", validate=validate_url)
    second_level_domain = utility.extract_second_level_domain(target_url)
    if not target_url.startswith('https') and not target_url.startswith('http'):
        target_url = 'https://' + target_url
    article_link_selector = get_input("Enter the CSS selector to find the links", default="h2 a")
    next_page_selector = get_input("Enter the CSS selector to find the next page link",default=None)
    proxy_pool_url = get_input("Enter the URL of the proxy pool", default= 'http://localhost:5555/random')
    article_title_selector = get_input("Enter the CSS selector to find the title", default="h2 a")
    article_content_selector = get_input("Enter the CSS selector to find the content", default="div.posthaven-post-body")
    custom_metadata = get_input("Do you want to customize book metadata?", default="n")
    if custom_metadata != "n":
        metadata = get_book_metadata()
    else:
        metadata = {'book_language':'en'}

    crawler = Crawler(proxy_pool_url)
    toc_manager = TOCManager(crawler, utility)
    article_downloader = ArticleDownloader(crawler, utility)
    article_manager = ArticleManager(toc_manager, article_downloader)

    toc = article_manager.generate_and_save_toc(target_url, article_link_selector, next_page_selector)
    article_manager.download_articles(toc, article_title_selector, article_content_selector)
    epub_generator = EpubGenerator('temp')
    epub_generator.generate_epub(toc_list = toc, title = second_level_domain, author = second_level_domain, language =      metadata['book_language'],epub_name=second_level_domain)