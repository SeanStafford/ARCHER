"""
Persistent SQLite database for querying resume content.

Provides a relational interface to resume items across documents, enabling
efficient queries by section type, company, skills, etc.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from archer.contexts.templating.resume_data_structure import ResumeDocument


class ResumeDatabase:
    """
    SQLite database for querying resume items.

    Stores all items (skills, bullets) from resume documents in a flat table
    with hierarchical metadata (section, subsection, company, etc.) for flexible queries.

    The database is persistent - build once with from_archive(), then load later
    by instantiating with the db_path.
    """

    leaf_sections = (
        "skill_list_caps",
        "skill_list_pipes",
        "personality_alias_array",
        "personality_bottom_bar",
    )

    branch_sections = ("projects", "skill_categories")

    def __init__(self, db_path: Path):
        """
        Load an existing database from disk.

        To create a new database, use ResumeDatabase.from_documents() instead.

        Args:
            db_path: Path to existing SQLite database file

        Raises:
            FileNotFoundError: If database file doesn't exist
        """
        self.db_path = db_path

        # Enforce that database must already exist
        if not db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {db_path}\n"
                f"To create a new database, use ResumeDatabase.from_documents()"
            )

        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name

    @classmethod
    def from_documents(cls, documents: List[ResumeDocument], db_path: Path) -> "ResumeDatabase":
        """
        Build new database from list of documents (deletes existing database).

        Args:
            documents: List of ResumeDocument instances
            db_path: Path where database will be created

        Returns:
            ResumeDatabase with all items from documents
        """
        # Delete existing database if present
        if db_path.exists():
            db_path.unlink()

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create new database connection and schema (bypassing __init__ validation)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Create schema
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                resume_name TEXT NOT NULL,
                path TEXT NOT NULL,

                section_name TEXT NOT NULL,
                section_type TEXT NOT NULL,
                subsection_name TEXT,
                subsection_type TEXT,

                item_text TEXT NOT NULL,
                item_order INTEGER NOT NULL,

                company TEXT,
                job_title TEXT,
                dates TEXT,
                project_name TEXT
            )
        """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_section_type ON items(section_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_resume_name ON items(resume_name)")
        conn.commit()
        conn.close()

        # Now load the newly created database via __init__
        db = cls(db_path)

        # Add all documents
        for doc in documents:
            db._add_resume(doc)

        db.conn.commit()
        return db

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dicts.

        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            List of dicts with column names as keys
        """
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_items_by_section_type(self, *section_types: str) -> List[Dict[str, Any]]:
        """
        Get all items from sections of given type(s).

        Args:
            section_types: One or more section type names

        Returns:
            List of item dicts matching section types
        """
        placeholders = ",".join("?" * len(section_types))
        return self.query(
            f"SELECT * FROM items WHERE section_type IN ({placeholders})",
            section_types,
        )

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Get all items from skill sections across all resumes."""
        return self.get_items_by_section_type(
            "skill_list_caps", "skill_list_pipes", "skill_category", "skill_categories"
        )

    def get_all_bullets(self) -> List[Dict[str, Any]]:
        """Get all bullet items from work experience and projects."""
        return self.get_items_by_section_type(
            "work_history", "projects", "work_experience", "project"
        )

    def _add_resume(self, doc: ResumeDocument):
        """
        Extract all items from a ResumeDocument and insert into database.

        Args:
            doc: ResumeDocument to extract items from
        """
        row_fields = {
            "resume_name": doc.filename,
            "path": doc.source_path,
        }
        for section in doc.sections:
            self._add_section_items(section, row_fields.copy())

    def _add_row(
        self,
        resume_name: str,
        path: str,
        section_name: str,
        section_type: str,
        item_text: str,
        item_order: int,
        subsection_name: str = None,
        subsection_type: str = None,
        company: str = None,
        job_title: str = None,
        dates: str = None,
        project_name: str = None,
    ):
        """
        Insert a single item row into the database.

        Required args (positional):
            resume_name: Resume filename (e.g., "Res202507_MLOps_Revature")
            path: Full path to resume YAML file
            section_name: Section name (e.g., "Core Skills", "Experience")
            section_type: Section type (e.g., "skill_list_caps", "work_history")
            item_text: The actual text content (skill, bullet, etc.)
            item_order: Position within section/subsection

        Optional args (defaults to None):
            subsection_name: Subsection name (e.g., company name, skill category name)
            subsection_type: Subsection type (e.g., "work_experience", "project")
            company: Company name (for work items)
            job_title: Job title (for work items)
            dates: Date range (for work/education items)
            project_name: Project name (for project bullets)
        """
        self.conn.execute(
            """
            INSERT INTO items (
                resume_name, path, section_name, section_type,
                subsection_name, subsection_type,
                item_text, item_order,
                company, job_title, dates, project_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resume_name,
                path,
                section_name,
                section_type,
                subsection_name,
                subsection_type,
                item_text,
                item_order,
                company,
                job_title,
                dates,
                project_name,
            ),
        )

    def _add_section_items(self, section, row_fields: dict):
        """Extract items from a section and insert into database."""
        section_name = section.name
        section_type = section.section_type

        # Add section-level fields
        row_fields.update({"section_name": section_name, "section_type": section_type})

        # Work history uses special flattened format from _parse_work_experience()
        if section_type == "work_history":
            subsections = section.data.get("subsections", [])
            for subsection in subsections:
                self._add_work_history_items(subsection, row_fields.copy())

        # Branch sections (have subsections) use standard format
        elif section_type in self.branch_sections:
            subsections = section.data.get("subsections", [])
            for subsection in subsections:
                self._add_wrapper_subsection_items(subsection, row_fields.copy())

        # Handle leaf sections (no subsections - items directly in section)
        elif section_type in self.leaf_sections:
            items = section.data["items"]
            self._add_items(items, row_fields)

    def _add_items(self, items: list, row_fields: dict):
        """
        Leaf method: iterate over items/bullets and insert rows.

        All metadata extraction happens in higher-level methods.
        This method only handles the final iteration and row insertion.

        Args:
            items: List of text items (skills, bullets, etc.)
            row_fields: Dict with all metadata fields already populated
        """
        for idx, item in enumerate(items):
            self._add_row(**row_fields, item_text=item, item_order=idx)

    def _add_work_history_items(self, subsection: Dict, row_fields: dict):
        """
        Extract items from work_history subsection (flattened format).

        work_history subsections use flattened format from _parse_work_experience():
        {company, title, dates, items: [...], projects: [{items: [...]}]}
        """
        company = subsection.get("company")
        job_title = subsection.get("title")
        dates = subsection.get("dates")

        # Add work_experience-level fields
        row_fields.update(
            {
                "subsection_name": company,
                "subsection_type": "work_experience",
                "company": company,
                "job_title": job_title,
                "dates": dates,
            }
        )

        # Add work_experience items
        items = subsection.get("items", [])
        self._add_items(items, row_fields)

        # Add nested project items
        projects = subsection.get("projects", [])
        for project in projects:
            proj_fields = row_fields.copy()
            proj_fields.update({"subsection_type": "project", "project_name": project["name"]})
            proj_items = project.get("items", [])
            self._add_items(proj_items, proj_fields)

    def _add_wrapper_subsection_items(self, subsection: Dict, row_fields: dict):
        """
        Extract items from wrapper subsections (skill_category or project).
        """
        subsection_type = subsection["type"]
        subsection_name = subsection["name"]

        # Add subsection-level fields
        row_fields.update(
            {
                "subsection_name": subsection_name,
                "subsection_type": subsection_type,
            }
        )

        # project subsections also get project_name
        if subsection_type == "project":
            row_fields["project_name"] = subsection_name

        items = subsection["items"]
        self._add_items(items, row_fields)
