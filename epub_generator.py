from ebooklib import epub
import os
import uuid

class EpubGenerator:
    
    def __init__(self, base_dir, output_dir=None):
        self.base_dir = base_dir
        self.output_dir = output_dir if output_dir else base_dir
        self.IMAGE_EXTENSIONS = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif'
    }

    def _generate_uuid(self):
        return str(uuid.uuid4())
    
    def add_chapters_to_book(self, book, toc_list):
        chapters = []
        added_files = set()
        for entry in toc_list:
            chapter_title = entry['chapter_title']
            chapter_file_name = entry['filename']
            chapter_file_path = os.path.join(self.base_dir, chapter_file_name)
            if chapter_file_name in added_files:
                continue
            try:
                with open(chapter_file_path, 'r', encoding='utf-8') as f:
                    chapter_content = f.read()
                c = epub.EpubHtml(title=chapter_title, file_name=chapter_file_name, content=chapter_content, media_type="application/xhtml+xml")
                book.add_item(c)
                chapters.append(c)
                added_files.add(chapter_file_name)
            except Exception as e:
                print(e)
                continue
        return chapters
    
    def add_images_to_book(self, book):
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.IMAGE_EXTENSIONS:
                    image_path = os.path.join(root, file)
                    if not os.path.exists(image_path):
                        print(f"Resource not found: {image_path}")
                        continue
                    img = epub.EpubImage()
                    img.file_name = file
                    img.media_type = self.IMAGE_EXTENSIONS[ext]
                    with open(image_path, 'rb') as f:
                        img.content = f.read()
                    book.add_item(img)
                    
    def generate_epub(self, toc_list, book_name, author, language, epub_name,cover_path,identifier=None):
        print("Generating epub...")
        # 创建保存目录
        os.makedirs(self.output_dir,exist_ok=True)

        book = epub.EpubBook()

        # 设置书籍的基本元数据
        if not identifier:
            identifier = self._generate_uuid()
        book.set_identifier(identifier)
        book.set_title(book_name)
        book.set_language(language)
        book.add_author(author)
        with open(cover_path, 'rb') as cover_file:
            book.set_cover("cover.jpg", cover_file.read())

        # 使用辅助方法添加章节和图片
        chapters = self.add_chapters_to_book(book, toc_list)
        self.add_images_to_book(book)

        # 创建导航文档
        nav_doc = epub.EpubNav()
        toc_links = [(c, c.title) for c in chapters]
        nav_doc.toc = toc_links
        book.add_item(nav_doc)

        # 定义书脊
        book.spine = ['nav'] + chapters
        book.toc = toc_links

        # 将书写入一个EPUB文件
        epub_path = os.path.join(self.output_dir, epub_name+'.epub')
        epub.write_epub(epub_path, book)

        print(f"EPUB generated at {epub_path}")
                