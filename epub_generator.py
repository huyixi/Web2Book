from ebooklib import epub
import os

class EpubGenerator:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        
    def generate_epub(self,toc_list):
        print("Generating epub...")
        book = epub.EpubBook()
        book.set_identifier('id123456')
        book.set_title('Sample book')
        book.set_language('en')
        book.add_author('huyixi')

        chapters = []
        added_files = set()
        for entry in toc_list:
            chapter_title = entry['title']
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
        
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_path = os.path.join(root, file)

                    # Verify if the resource exists
                    if not os.path.exists(image_path):
                        print(f"Resource not found: {image_path}")
                        continue

                    img = epub.EpubImage()
                    img.file_name = file
                    img.media_type = "image/" + file.split('.')[-1]
                    with open(image_path, 'rb') as f:
                        img.content = f.read()
                    book.add_item(img)

        # Create Navigation (NAV) Document
        toc_links = [(c, c.title) for c in chapters]
        nav_doc = epub.EpubNav()
        nav_doc.toc = toc_links
        book.add_item(nav_doc)

        # Define book spine
        book.spine = ['nav'] + chapters
        # Write the book as an EPUB file
        epub_name = self.base_dir + '.epub'
        epub.write_epub(epub_name, book)
