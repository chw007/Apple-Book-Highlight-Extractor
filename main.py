import os
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Highlight:
    text: str
    created_at: datetime
    book_title: str
    chapter: Optional[str] = None
    note: Optional[str] = None

class BookHighlightExtractor:
    def __init__(self):
        self.annotation_db_path, self.library_db_path = self._get_database_path()
        self.annotation_conn = None
        self.library_conn = None

    def _get_database_path(self) -> tuple[Path, Optional[Path]]:
        """Get the path to Apple Books database and library database"""
        home = Path.home()
        containers_path = home / "Library/Containers"
        
        # Updated search patterns for database files
        annotation_patterns = [
            "**/BKAnnotation/*.sqlite",
            "**/AEAnnotation/*.sqlite",
        ]
        
        library_patterns = [
            "**/com.apple.iBooksX/Data/Documents/BKLibrary/*.sqlite",
            "**/com.apple.iBooks/Data/Documents/BKLibrary/*.sqlite",
            "**/BKLibrary/*.sqlite",
        ]
        
        print("\nSearching for database files...")
        
        # Search in all containers related to Books
        book_containers = [
            d for d in containers_path.glob("*") 
            if d.is_dir() and any(x in d.name.lower() for x in ["book", "bk", "annotation"])
        ]
        
        annotation_db = None
        library_db = None
        
        for container in book_containers:
            print(f"\nChecking container: {container.name}")
            
            # Look for annotation database
            for pattern in annotation_patterns:
                for db_path in container.glob(pattern):
                    print(f"Found annotation database: {db_path}")
                    annotation_db = db_path
            
            # Look for library database
            for pattern in library_patterns:
                for db_path in container.glob(pattern):
                    print(f"Found library database: {db_path}")
                    library_db = db_path
        
        if not annotation_db:
            # Default annotation database path
            annotation_db = home / "Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/annotations.sqlite"
            print(f"\nNo annotation database found. Will use default path: {annotation_db}")
        
        return annotation_db, library_db

    def connect(self):
        """Connect to the SQLite databases"""
        if not self.annotation_db_path.exists():
            raise FileNotFoundError(f"Annotation database not found at {self.annotation_db_path}")
        self.annotation_conn = sqlite3.connect(self.annotation_db_path)
        self.annotation_conn.row_factory = sqlite3.Row
        
        if self.library_db_path and self.library_db_path.exists():
            self.library_conn = sqlite3.connect(self.library_db_path)
            self.library_conn.row_factory = sqlite3.Row

    def get_book_title(self, asset_id: str) -> Optional[str]:
        """Get book title from library database using asset ID"""
        if not self.library_conn:
            return None
        
        try:
            # Try different possible table and column names
            queries = [
                "SELECT ZTITLE FROM ZBKLIBRARYASSET WHERE ZASSETID = ?",
                "SELECT ZTITLE FROM ZBKLIBRARYASSET WHERE ZBKASSETID = ?",
                "SELECT ZTITLE FROM ZBKLIBRARY WHERE ZASSETID = ?"
            ]
            
            for query in queries:
                try:
                    cursor = self.library_conn.execute(query, (asset_id,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                except sqlite3.OperationalError:
                    continue
                
        except Exception as e:
            print(f"Error getting book title: {e}")
        
        return None

    def get_highlights(self, book_title: Optional[str] = None) -> List[Highlight]:
        """
        Fetch highlights from the database, optionally filtered by book title
        
        Args:
            book_title: Optional book title to filter highlights
        """
        if not self.annotation_conn:
            self.connect()

        cursor = self.annotation_conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
            ORDER BY name;
        """)
        tables = [row[0] for row in cursor]
        print("\nAvailable tables in database:", tables)

        query = """
        SELECT 
            ZANNOTATIONSELECTEDTEXT as text,
            ZANNOTATIONCREATIONDATE as created_at,
            ZANNOTATIONNOTE as note,
            ZANNOTATIONASSETID as book_id,
            ZANNOTATIONREPRESENTATIVETEXT as representative_text,
            ZANNOTATIONTYPE as annotation_type,
            ZANNOTATIONISUNDERLINE as is_underline
        FROM ZAEANNOTATION
        WHERE ZANNOTATIONSELECTEDTEXT IS NOT NULL
            AND ZANNOTATIONDELETED = 0
        ORDER BY ZANNOTATIONCREATIONDATE DESC
        """

        try:
            cursor = self.annotation_conn.execute(query)
            highlights = []
            
            for row in cursor:
                created_at_timestamp = row['created_at']
                if created_at_timestamp:
                    created_at = datetime.fromtimestamp(created_at_timestamp + 978307200)
                else:
                    created_at = datetime.now()

                text = row['text']
                if row['representative_text']:
                    text = f"{text}\n\nContext: {row['representative_text']}"

                note = row['note'] or ""
                if row['annotation_type'] is not None:
                    note_prefix = "Underline" if row['is_underline'] else "Highlight"
                    if note:
                        note = f"{note_prefix}\n{note}"
                    else:
                        note = note_prefix

                current_book_title = None
                if row['book_id']:
                    current_book_title = self.get_book_title(row['book_id'])
                
                # Skip if we're filtering by book title and this isn't the right book
                if book_title and current_book_title and book_title.lower() not in current_book_title.lower():
                    continue
                
                highlight = Highlight(
                    text=text,
                    created_at=created_at,
                    book_title=current_book_title or f"Book ID: {row['book_id']}" if row['book_id'] else 'Unknown Book',
                    chapter=None,
                    note=note
                )
                highlights.append(highlight)
            
            if highlights:
                print(f"\nSuccessfully extracted {len(highlights)} highlights")
                return highlights
            elif book_title:
                print(f"\nNo highlights found for book: {book_title}")
            else:
                print("\nNo highlights found")

        except sqlite3.OperationalError as e:
            print(f"\nQuery failed: {e}")

        print("\nFalling back to book information only.")
        return self._get_book_info(book_title)

    def _get_book_info(self, book_title: Optional[str] = None) -> List[Highlight]:
        """Fallback method to get only book information"""
        query = """
        SELECT 
            ZTITLE as book_title,
            ZAUTHOR as author,
            ZREADINGPROGRESS as progress,
            ZLASTOPENDATE as last_opened,
            ZBOOKDESCRIPTION as description,
            ZGENRE as genre
        FROM ZBKLIBRARYASSET
        WHERE ZTITLE IS NOT NULL
        """
        
        if book_title:
            query += " AND LOWER(ZTITLE) LIKE LOWER(?)"
            cursor = self.library_conn.execute(query, (f"%{book_title}%",))
        else:
            query += " ORDER BY ZLASTOPENDATE DESC"
            cursor = self.library_conn.execute(query)
        
        highlights = []
        
        for row in cursor:
            highlight = Highlight(
                text=f"Progress: {row['progress']*100:.1f}%" if row['progress'] is not None else "No progress data",
                created_at=datetime.fromtimestamp(row['last_opened'] + 978307200) if row['last_opened'] else datetime.now(),
                book_title=row['book_title'],
                chapter=row['genre'] if row['genre'] else None,
                note=f"Author: {row['author']}\nDescription: {row['description']}" if row['author'] or row['description'] else None
            )
            highlights.append(highlight)
        
        return highlights

    def export_to_markdown(self, output_path: Path, book_title: Optional[str] = None):
        """
        Export highlights to a markdown file
        
        Args:
            output_path: Path to save the markdown file
            book_title: Optional book title to filter highlights
        """
        highlights = self.get_highlights(book_title)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            current_book = None
            
            for highlight in highlights:
                if highlight.book_title != current_book:
                    current_book = highlight.book_title
                    f.write(f"\n## {current_book}\n\n")
                
                f.write(f"> {highlight.text}\n")
                if highlight.note:
                    f.write(f"\nNote: {highlight.note}\n")
                f.write(f"\n- Chapter: {highlight.chapter or 'N/A'}\n")
                f.write(f"- Date: {highlight.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

def main():
    extractor = BookHighlightExtractor()
    
    try:
        # Get user input for book title
        print("\nEnter a book title to export highlights (or press Enter for all books):")
        book_title = input("> ").strip()
        
        # Create output filename based on input
        if book_title:
            safe_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_'))
            output_path = Path.home() / "Desktop" / f"book_highlights_{safe_title}.md"
        else:
            output_path = Path.home() / "Desktop" / "book_highlights_all.md"
        
        # Export highlights
        extractor.export_to_markdown(output_path, book_title)
        print(f"Highlights exported successfully to {output_path}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    extractor = BookHighlightExtractor()
    print("\nSystem Information:")
    print(f"Home directory: {Path.home()}")
    print(f"Library exists: {(Path.home() / 'Library').exists()}")
    print(f"Books container exists: {(Path.home() / 'Library/Containers/com.apple.Books').exists()}")
    print(f"\nSelected database path: {extractor.annotation_db_path}")
    print(f"Database exists: {extractor.annotation_db_path.exists()}\n")
    main() 