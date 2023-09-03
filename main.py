import inquirer
import validators
import re
from crawler import Crawler
from article_manager import ArticleManager, TOCManager, ArticleDownloader, Utility, ImageHandler
from epub_generator import EpubGenerator


def get_input(message, default=None, validate=None):
    if validate:
        questions = [inquirer.Text('input', message=message, default=default, validate=validate)]
    else:
        questions = [inquirer.Text('input', message=message, default=default)]
    answers = inquirer.prompt(questions)
    return answers['input']

def ensure_url_scheme(url):
    if not url.startswith(("https://","http://")):
        return 'https://' + url
    return url

def validate_url(answers, url):
    if validators.url(url) or validators.url('http://' + url) or re.match(r'http://localhost:\d+', url):
        return True
    return False

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
    target_url = get_input("Enter the URL of the website to be crawled",default="https://developer.chrome.com/docs/extensions/mv3/", validate=validate_url)
    second_level_domain = utility.extract_second_level_domain(target_url)
    target_url = ensure_url_scheme(target_url)
    article_link_selector = get_input("Enter the CSS selector to find the links",default="a.navigation-tree__link")
    next_page_selector = get_input("Enter the CSS selector to find the next page link",default=None)
    article_selector = get_input("Enter the CSS selector to find the content", default="article")
    remove_selectors = get_input("Enter the CSS selector to remove specify element(Seperate by ;)", default=None)
    remove_selectors = [selector.strip() for selector in remove_selectors.split(";")]
    proxy_pool_url = get_input("Enter the URL of the proxy pool", default="http://localhost:5555/random")
    custom_metadata = get_input("Do you want to customize book metadata?", default="n")
    if custom_metadata != "n":
        metadata = get_book_metadata()
    else:
        metadata = {'book_language':'zh'}

    crawler = Crawler(proxy_pool_url)
    image_handler = ImageHandler(crawler, utility)
    toc_manager = TOCManager(crawler, utility)
    article_downloader = ArticleDownloader(crawler, utility, image_handler)
    article_manager = ArticleManager(toc_manager, article_downloader)
    
    toc = article_manager.generate_and_save_toc(target_url, article_link_selector, next_page_selector)
    article_manager.download_articles(toc, article_selector, remove_selectors)
    epub_generator = EpubGenerator('tmp/')
    image_handler.generate_book_cover(second_level_domain)
    epub_generator.generate_epub(toc_list = toc, book_name = second_level_domain, author = second_level_domain, language = metadata['book_language'],epub_name=second_level_domain, cover_path="tmp/cover.jpg")