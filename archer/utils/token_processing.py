"""
Standardized text tokenization utilities.

Provides configurable tokenization with optional normalization steps:
- Stopword removal (NLTK)
- Lemmatization or stemming (NLTK)
- Phrase normalization (acronym expansion/contraction)
- Equivalent terms mapping (derivational morphology)
- N-gram generation

Designed to be domain-agnostic - all domain-specific mappings are passed in,
not hardcoded. Can be used standalone or passed to sklearn's TfidfVectorizer.

Usage:
    from archer.utils.token_processing import Tokenizer

    # Basic usage with defaults
    tokenizer = Tokenizer()
    tokens = tokenizer.tokenize("Machine learning is useful")

    # With domain-specific mappings
    tokenizer = Tokenizer(
        phrase_contract_map={"machine learning": "ml"},
        equivalent_terms={"agentic": "agent"},
    )

    # With sklearn TfidfVectorizer
    from sklearn.feature_extraction.text import TfidfVectorizer
    vectorizer = TfidfVectorizer(tokenizer=tokenizer)
"""

import hashlib
import json
import re
import sqlite3
import warnings
from datetime import datetime
from typing import Optional

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.util import ngrams


def _compile_phrase_patterns(phrase_map: dict[str, str]) -> list[tuple[re.Pattern, str]]:
    """Compile regex patterns for phrase replacement, sorted by length (longest first)."""
    sorted_phrases = sorted(phrase_map.keys(), key=len, reverse=True)
    return [
        (re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE), replacement)
        for phrase, replacement in [(p, phrase_map[p]) for p in sorted_phrases]
    ]


class Tokenizer:
    """
    Configurable tokenizer with normalization pipeline.

    Pipeline order:
    1. Phrase expansion (ambiguous acronyms -> full form)
    2. Phrase contraction (full phrases -> canonical form)
    3. Tokenization (word boundary regex)
    4. Lowercase
    5. Stopword removal
    6. Lemmatization OR stemming
    7. Equivalent terms mapping
    8. Min length filtering
    9. N-gram generation (optional)

    The tokenizer is callable, making it compatible with sklearn's
    TfidfVectorizer(tokenizer=...) parameter.
    """

    def __init__(
        self,
        acronym_expand_map: Optional[dict[str, str]] = None,
        phrase_contract_map: Optional[dict[str, str]] = None,
        equivalent_terms: Optional[dict[str, str]] = None,
        lowercase: bool = True,
        use_stopwords: bool = True,
        custom_stopwords: Optional[set[str]] = None,
        use_lemmatization: bool = True,
        use_stemming: bool = False,
        min_token_length: int = 2,
        max_ngram: int = 1,
    ):
        """
        Initialize tokenizer.

        Args:
            acronym_expand_map: Ambiguous acronyms -> expanded form (e.g., {"cv": "computer_vision"})
            phrase_contract_map: Phrases -> canonical form (e.g., {"machine learning": "ml"})
            equivalent_terms: Post-lemmatization term mapping (e.g., {"agentic": "agent"})
            lowercase: Whether to lowercase tokens
            use_stopwords: Whether to remove stopwords
            custom_stopwords: Custom stopword set (uses NLTK English if None)
            use_lemmatization: Whether to apply lemmatization (takes precedence over stemming)
            use_stemming: Whether to apply stemming (ignored if use_lemmatization=True)
            min_token_length: Minimum token length to keep
            max_ngram: Maximum n-gram size (1 = unigrams only, 2 = unigrams + bigrams, etc.)
        """
        self.acronym_expand_map = acronym_expand_map or {}
        self.phrase_contract_map = phrase_contract_map or {}
        self.equivalent_terms = equivalent_terms or {}
        self.lowercase = lowercase
        self.use_stopwords = use_stopwords
        self.min_token_length = min_token_length
        self.max_ngram = max_ngram

        # Compile phrase patterns for two-pass normalization:
        self._expand_patterns = _compile_phrase_patterns(self.acronym_expand_map)
        self._contract_patterns = _compile_phrase_patterns(self.phrase_contract_map)

        # Load stopwords
        if use_stopwords:
            self._stopwords = custom_stopwords if custom_stopwords else self._load_stopwords()
        else:
            self._stopwords = set()

        # Load lemmatizer or stemmer (lemmatization takes precedence)
        self._lemmatizer = None
        self._stemmer = None
        if use_lemmatization:
            self._lemmatizer = self._load_lemmatizer()
            if use_stemming:
                warnings.warn(
                    "Both use_lemmatization and use_stemming are True, but cannot use both. Only using lemmatization."
                )
        elif use_stemming:
            self._stemmer = PorterStemmer()

    def _load_stopwords(self) -> set[str]:
        """Load NLTK English stopwords, downloading if necessary."""
        try:
            return set(stopwords.words("english"))
        except LookupError:
            nltk.download("stopwords", quiet=True)
            return set(stopwords.words("english"))

    def _load_lemmatizer(self) -> WordNetLemmatizer:
        """Load NLTK WordNetLemmatizer, downloading if necessary."""
        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            nltk.download("wordnet", quiet=True)
        return WordNetLemmatizer()

    def _normalize_phrases(self, text: str) -> str:
        """
        Apply two-pass phrase normalization.

        1. Expand ambiguous acronyms to full form (e.g., "cv" -> "computer_vision")
        2. Contract known phrases to canonical form (e.g., "machine learning" -> "ml")
        """
        for pattern, expanded in self._expand_patterns:
            text = pattern.sub(expanded, text)
        for pattern, canonical in self._contract_patterns:
            text = pattern.sub(canonical, text)
        return text

    def _lemmatize(self, token: str) -> str:
        """Lemmatize a single token, trying verb then noun form."""
        # Try verb form first (handles "experienced" -> "experience")
        lemma_v = self._lemmatizer.lemmatize(token, pos="v")
        if lemma_v != token:
            return lemma_v
        # Fall back to noun form (handles "experiences" -> "experience")
        return self._lemmatizer.lemmatize(token, pos="n")

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize text with full normalization pipeline.

        Returns:
            List of normalized tokens
        """
        if not text:
            return []

        # Step 1-2: Phrase normalization
        text = self._normalize_phrases(text)

        # Step 3: Tokenization (word boundaries)
        tokens = re.findall(r"\b\w+\b", text)

        # Step 4: Lowercase
        if self.lowercase:
            tokens = [t.lower() for t in tokens]

        # Step 5: Stopword removal
        if self._stopwords:
            tokens = [t for t in tokens if t not in self._stopwords]

        # Step 6: Lemmatization or stemming
        if self._lemmatizer:
            tokens = [self._lemmatize(t) for t in tokens]
        elif self._stemmer:
            tokens = [self._stemmer.stem(t) for t in tokens]

        # Step 7: Equivalent terms mapping
        if self.equivalent_terms:
            tokens = [self.equivalent_terms.get(t, t) for t in tokens]

        # Step 8: Min length filtering (also filter pure numbers)
        if self.min_token_length > 0:
            tokens = [t for t in tokens if len(t) >= self.min_token_length and not t.isdigit()]

        # Step 9: N-gram generation
        if self.max_ngram > 1:
            base_tokens = tokens.copy()
            for n in range(2, self.max_ngram + 1):
                tokens.extend("_".join(gram) for gram in ngrams(base_tokens, n))

        return tokens

    def __call__(self, text: str) -> list[str]:
        """Make tokenizer callable for sklearn compatibility."""
        return self.tokenize(text)

    def get_config_dict(self) -> dict:
        """Return tokenizer settings as a dictionary."""
        return {
            "acronym_expand_map": self.acronym_expand_map,
            "phrase_contract_map": self.phrase_contract_map,
            "equivalent_terms": self.equivalent_terms,
            "lowercase": self.lowercase,
            "use_stopwords": self.use_stopwords,
            "use_lemmatization": self._lemmatizer is not None,
            "use_stemming": self._stemmer is not None,
            "min_token_length": self.min_token_length,
            "max_ngram": self.max_ngram,
        }


class CorpusTokenizer(Tokenizer):
    """
    Tokenizer with corpus persistence via SQLite.

    Extends Tokenizer to save/load tokenized corpora to a database.
    Multiple tokenization configs can coexist in the same database,
    identified by a hash of their settings.

    Usage:
        tokenizer = CorpusTokenizer(
            db_path="tokens.db",
            use_lemmatization=True,
            phrase_contract_map={"machine learning": "ml"},
        )

        # Tokenize and save
        tokenizer.tokenize_and_save(["doc one", "doc two"], doc_ids=["d1", "d2"])

        # Load previously tokenized corpus
        corpus = tokenizer.load_corpus()  # list[list[str]]

        # List all configs in database
        configs = tokenizer.list_configs()
    """

    def __init__(
        self,
        db_path: str,
        acronym_expand_map: Optional[dict[str, str]] = None,
        phrase_contract_map: Optional[dict[str, str]] = None,
        equivalent_terms: Optional[dict[str, str]] = None,
        lowercase: bool = True,
        use_stopwords: bool = True,
        custom_stopwords: Optional[set[str]] = None,
        use_lemmatization: bool = True,
        use_stemming: bool = False,
        min_token_length: int = 2,
        max_ngram: int = 1,
    ):
        """
        Initialize corpus tokenizer with database path.

        Args:
            db_path: Path to SQLite database file
            (remaining args passed to Tokenizer)
        """
        super().__init__(
            acronym_expand_map=acronym_expand_map,
            phrase_contract_map=phrase_contract_map,
            equivalent_terms=equivalent_terms,
            lowercase=lowercase,
            use_stopwords=use_stopwords,
            custom_stopwords=custom_stopwords,
            use_lemmatization=use_lemmatization,
            use_stemming=use_stemming,
            min_token_length=min_token_length,
            max_ngram=max_ngram,
        )
        self.db_path = db_path
        config = self.get_config_dict()
        canonical = json.dumps(config, sort_keys=True, default=str)
        self.config_hash = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokenizer_config (
                    config_hash TEXT PRIMARY KEY,
                    config_json TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    config_hash TEXT REFERENCES tokenizer_config(config_hash) ON DELETE CASCADE,
                    doc_order INTEGER,
                    doc_id TEXT,
                    tokens_json TEXT,
                    PRIMARY KEY (config_hash, doc_order)
                )
            """)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

    def _config_exists(self) -> bool:
        """Check if current config already exists in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM tokenizer_config WHERE config_hash = ?",
                (self.config_hash,),
            )
            return cursor.fetchone() is not None

    def save_corpus(
        self,
        tokenized_corpus: list[list[str]],
        doc_ids: Optional[list[str]] = None,
    ) -> None:
        """
        Save an already-tokenized corpus to the database.

        If config exists, overwrites existing documents.
        If config doesn't exist, creates new config entry.

        Args:
            tokenized_corpus: List of token lists (already tokenized)
            doc_ids: Optional document identifiers (defaults to index)
        """
        if doc_ids is None:
            doc_ids = [str(i) for i in range(len(tokenized_corpus))]

        if len(doc_ids) != len(tokenized_corpus):
            raise ValueError("doc_ids length must match corpus length")

        now = datetime.now().isoformat()
        config_json = json.dumps(self.get_config_dict(), indent=2)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            if self._config_exists():
                conn.execute(
                    "DELETE FROM documents WHERE config_hash = ?",
                    (self.config_hash,),
                )
                conn.execute(
                    "UPDATE tokenizer_config SET updated_at = ? WHERE config_hash = ?",
                    (now, self.config_hash),
                )
            else:
                conn.execute(
                    "INSERT INTO tokenizer_config (config_hash, config_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (self.config_hash, config_json, now, now),
                )

            conn.executemany(
                "INSERT INTO documents (config_hash, doc_order, doc_id, tokens_json) VALUES (?, ?, ?, ?)",
                [
                    (self.config_hash, i, doc_id, json.dumps(tokens))
                    for i, (doc_id, tokens) in enumerate(zip(doc_ids, tokenized_corpus))
                ],
            )
            conn.commit()

    def load_corpus(self) -> list[list[str]]:
        """
        Load tokenized corpus for current config from database.

        Returns:
            List of token lists, ordered by doc_order
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT tokens_json FROM documents WHERE config_hash = ? ORDER BY doc_order",
                (self.config_hash,),
            )
            rows = cursor.fetchall()

        if not rows:
            raise KeyError(f"No corpus found for config hash: {self.config_hash}")

        return [json.loads(row[0]) for row in rows]

    def load_corpus_with_ids(self) -> list[tuple[str, list[str]]]:
        """
        Load tokenized corpus with document IDs.

        Returns:
            List of (doc_id, tokens) tuples, ordered by doc_order
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT doc_id, tokens_json FROM documents WHERE config_hash = ? ORDER BY doc_order",
                (self.config_hash,),
            )
            rows = cursor.fetchall()

        if not rows:
            raise KeyError(f"No corpus found for config hash: {self.config_hash}")

        return [(row[0], json.loads(row[1])) for row in rows]

    def tokenize_and_save(
        self,
        texts: list[str],
        doc_ids: Optional[list[str]] = None,
    ) -> list[list[str]]:
        """
        Tokenize texts and save to database.

        Args:
            texts: Raw text documents to tokenize
            doc_ids: Optional document identifiers

        Returns:
            The tokenized corpus (list of token lists)
        """
        tokenized = [self.tokenize(text) for text in texts]
        self.save_corpus(tokenized, doc_ids)
        return tokenized

    def list_configs(self) -> list[dict]:
        """
        List all tokenizer configs in the database.

        Returns:
            List of config dicts with hash, settings, timestamps, and doc count
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT c.config_hash, c.config_json, c.created_at, c.updated_at,
                       COUNT(d.doc_order) as doc_count
                FROM tokenizer_config c
                LEFT JOIN documents d ON c.config_hash = d.config_hash
                GROUP BY c.config_hash
            """)
            rows = cursor.fetchall()

        return [
            {
                "config_hash": row[0],
                "config": json.loads(row[1]),
                "created_at": row[2],
                "updated_at": row[3],
                "doc_count": row[4],
            }
            for row in rows
        ]

    def delete_corpus(self) -> bool:
        """
        Delete corpus for current config from database.

        Returns:
            True if deleted, False if config didn't exist
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.execute(
                "DELETE FROM tokenizer_config WHERE config_hash = ?",
                (self.config_hash,),
            )
            conn.commit()
            return cursor.rowcount > 0
