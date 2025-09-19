#!/usr/bin/env python3
"""
Script to translate French fields in the bibliography CSV to English.
Translates summary, keywords, and theme fields from French to English.
"""

import pandas as pd
import re
import unicodedata
from typing import Optional
from transformers import MarianMTModel, MarianTokenizer

# Initialize translation model (best French-English model)
model_name = "Helsinki-NLP/opus-mt-fr-en"
model = None
tokenizer = None

def init_translation_model():
    """Initialize the translation model (lazy loading)"""
    global model, tokenizer
    if model is None:
        print("Loading French-English translation model...")
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        print("Translation model loaded successfully!")

translation_counter = 0

def translate_with_model(text: str) -> str:
    """Translate text using the neural translation model"""
    global translation_counter

    if not text or pd.isna(text):
        return text

    # Skip if text is already mostly English
    if is_mostly_english(text):
        return text

    try:
        translation_counter += 1
        print(f"\n[Translation #{translation_counter}]")
        print(f"  Original: {text[:150]}..." if len(str(text)) > 150 else f"  Original: {text}")

        # Split long text into chunks to avoid model limits
        chunks = split_text_into_chunks(text, max_length=400)
        translated_chunks = []

        for chunk in chunks:
            if chunk.strip():
                # Tokenize and translate
                inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)
                translated = model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
                translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
                translated_chunks.append(translated_text)

        result = " ".join(translated_chunks)
        print(f"  → Translated: {result[:150]}..." if len(result) > 150 else f"  → Translated: {result}")
        return result
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def is_mostly_english(text: str) -> bool:
    """Check if text is mostly English based on common French indicators"""
    # Expanded list of French indicators including more common words and accented characters
    french_indicators = [
        'le ', 'la ', 'les ', 'du ', 'de la ', 'des ', 'ce ', 'cette ', 'ces ',
        'est ', 'sont ', 'dans ', 'sur ', 'avec ', 'pour ', 'par ', 'qui ', 'que ',
        'dont ', 'où ', 'à ', 'été ', 'être ', 'avoir ', 'faire ', 'dit ', 'fait ',
        'très ', 'bien ', 'peu ', 'même ', 'autre ', 'aussi ', 'leur ', 'tout ',
        'nous ', 'vous ', 'mais ', 'ou ', 'et ', 'donc ', 'car ', 'ni ', 'ne ',
        'créativité', 'artificielle', 'effondrement', 'réseau', 'système', 'développement',
        'étude', 'recherche', 'année', 'société', 'économie', 'politique'
    ]

    # Also check for French accented characters
    french_accents = ['é', 'è', 'ê', 'ë', 'à', 'â', 'ù', 'û', 'ü', 'ô', 'î', 'ï', 'ç', 'œ', 'æ']

    text_lower = text.lower()

    # Count French indicators
    french_count = sum(1 for indicator in french_indicators if indicator in text_lower)

    # Count French accented characters
    accent_count = sum(1 for accent in french_accents if accent in text_lower)

    # More aggressive detection: if ANY French indicators or multiple accented chars, translate it
    return french_count == 0 and accent_count < 2

def split_text_into_chunks(text: str, max_length: int = 400) -> list:
    """Split text into smaller chunks for translation"""
    if len(text) <= max_length:
        return [text]

    # Try to split at sentence boundaries
    sentences = re.split(r'[.!?]+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk + sentence) <= max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def translate_text(text: str) -> str:
    """
    Translate French text to English using pattern matching and common translations.
    This is a basic translation for academic/technical terms.
    """
    if not text or pd.isna(text):
        return text

    # Common French to English translations for academic/technical content
    translations = {
        # Academic terms
        "résumé": "summary",
        "mots-clés": "keywords",
        "mots clés": "keywords",
        "références bibliographiques": "bibliographic references",
        "références": "references",
        "auteur": "author",
        "titre": "title",
        "année": "year",
        "éditeur": "publisher",
        "chapitre": "chapter",
        "ouvrage": "work",
        "document": "document",
        "étude": "study",
        "recherche": "research",
        "analyse": "analysis",
        "thèse": "thesis",
        "article": "article",
        "livre": "book",
        "revue": "journal",
        "écritures": "writings",
        "écriture": "writing",

        # Technology terms
        "intelligence artificielle": "artificial intelligence",
        "réseaux sans fil": "wireless networks",
        "technologie": "technology",
        "informatique": "computer science",
        "numérique": "digital",
        "électronique": "electronic",
        "logiciel": "software",
        "matériel": "hardware",
        "système": "system",
        "algorithme": "algorithm",
        "données": "data",
        "base de données": "database",
        "réseau": "network",
        "internet": "internet",
        "web": "web",
        "site web": "website",
        "application": "application",
        "programme": "program",
        "programmation": "programming",
        "développement": "development",
        "innovation": "innovation",
        "évolution": "evolution",
        "transformation": "transformation",
        "automatisation": "automation",
        "robotique": "robotics",
        "cybernétique": "cybernetics",

        # Science terms
        "sciences": "sciences",
        "physique": "physics",
        "chimie": "chemistry",
        "biologie": "biology",
        "mathématiques": "mathematics",
        "géologie": "geology",
        "astronomie": "astronomy",
        "médecine": "medicine",
        "psychologie": "psychology",
        "sociologie": "sociology",
        "anthropologie": "anthropology",
        "philosophie": "philosophy",
        "histoire": "history",
        "géographie": "geography",
        "économie": "economics",
        "politique": "politics",
        "droit": "law",
        "éducation": "education",
        "enseignement": "teaching",
        "apprentissage": "learning",
        "formation": "training",
        "université": "university",
        "école": "school",
        "institut": "institute",
        "laboratoire": "laboratory",
        "centre": "center",
        "département": "department",
        "faculté": "faculty",

        # Art and culture terms
        "art": "art",
        "culture": "culture",
        "littérature": "literature",
        "musique": "music",
        "peinture": "painting",
        "sculpture": "sculpture",
        "architecture": "architecture",
        "théâtre": "theater",
        "cinéma": "cinema",
        "film": "film",
        "photographie": "photography",
        "design": "design",
        "esthétique": "aesthetics",
        "créativité": "creativity",
        "artistique": "artistic",
        "culturel": "cultural",
        "patrimonial": "heritage",
        "traditionnel": "traditional",
        "moderne": "modern",
        "contemporain": "contemporary",

        # Media and communication
        "médias": "media",
        "communication": "communication",
        "information": "information",
        "journalisme": "journalism",
        "presse": "press",
        "radio": "radio",
        "télévision": "television",
        "diffusion": "broadcasting",
        "publication": "publication",
        "édition": "publishing",
        "impression": "printing",

        # Social and political terms
        "société": "society",
        "social": "social",
        "public": "public",
        "privé": "private",
        "gouvernement": "government",
        "administration": "administration",
        "gestion": "management",
        "organisation": "organization",
        "institution": "institution",
        "entreprise": "enterprise",
        "industrie": "industry",
        "commerce": "commerce",
        "marché": "market",
        "économique": "economic",
        "financier": "financial",
        "commercial": "commercial",
        "industriel": "industrial",

        # Time and space
        "futur": "future",
        "avenir": "future",
        "présent": "present",
        "passé": "past",
        "historique": "historical",
        "actuel": "current",
        "nouveau": "new",
        "ancien": "old",
        "récent": "recent",
        "moderne": "modern",
        "traditionnel": "traditional",
        "global": "global",
        "international": "international",
        "national": "national",
        "régional": "regional",
        "local": "local",

        # Adjectives and descriptors
        "important": "important",
        "principal": "main",
        "majeur": "major",
        "mineur": "minor",
        "central": "central",
        "essentiel": "essential",
        "nécessaire": "necessary",
        "possible": "possible",
        "difficile": "difficult",
        "facile": "easy",
        "complexe": "complex",
        "simple": "simple",
        "avancé": "advanced",
        "basique": "basic",
        "général": "general",
        "spécifique": "specific",
        "particulier": "particular",
        "spécialisé": "specialized",

        # Specific phrases found in the CSV
        "enseignement supérieur artistique": "artistic higher education",
        "révolution industrielle": "industrial revolution",
        "changement climatique": "climate change",
        "réalité virtuelle": "virtual reality",
        "réalité augmentée": "augmented reality",
        "apprentissage à distance": "distance learning",
        "sciences cognitives": "cognitive sciences",
        "nanotechnologies": "nanotechnologies",
        "biotechnologies": "biotechnologies",
        "interface cerveau-machine": "brain-machine interface",
        "convergence technologique": "technological convergence",
        "quatrième révolution industrielle": "fourth industrial revolution",

        # Additional terms with accents and capitals
        "créativité": "creativity",
        "créative": "creative",
        "créatif": "creative",
        "créateurs": "creators",
        "créateur": "creator",
        "académique": "academic",
        "académiques": "academic",
        "économique": "economic",
        "économiques": "economic",
        "technologique": "technological",
        "technologiques": "technological",
        "industrielle": "industrial",
        "industrielles": "industrial",
        "culturelle": "cultural",
        "culturelles": "cultural",
        "scientifique": "scientific",
        "scientifiques": "scientific",
        "artistique": "artistic",
        "artistiques": "artistic",
        "éthique": "ethics",
        "éthiques": "ethical",
        "esthétique": "aesthetic",
        "esthétiques": "aesthetic",
        "théorie": "theory",
        "théories": "theories",
        "théorique": "theoretical",
        "théoriques": "theoretical",
        "pratique": "practice",
        "pratiques": "practices",
        "méthodologie": "methodology",
        "méthodologies": "methodologies",
        "pédagogie": "pedagogy",
        "pédagogique": "pedagogical",
        "pédagogiques": "pedagogical",
        "didactique": "didactic",
        "didactiques": "didactic",
        "numérique": "digital",
        "numériques": "digital",
        "électronique": "electronic",
        "électroniques": "electronic",
        "mémoire": "memory",
        "mémoires": "memories",
        "société": "society",
        "sociétés": "societies",
        "sociétal": "societal",
        "sociétaux": "societal",
        "humanité": "humanity",
        "humanités": "humanities",
        "identité": "identity",
        "identités": "identities",
        "réalité": "reality",
        "réalités": "realities",
        "qualité": "quality",
        "qualités": "qualities",
        "liberté": "freedom",
        "libertés": "freedoms",
        "égalité": "equality",
        "égalités": "equalities",
        "fraternité": "fraternity",
        "sécurité": "security",
        "propriété": "property",
        "propriétés": "properties",
        "activité": "activity",
        "activités": "activities",
        "capacité": "capacity",
        "capacités": "capacities",
        "possibilité": "possibility",
        "possibilités": "possibilities",
        "université": "university",
        "universités": "universities",
        "faculté": "faculty",
        "facultés": "faculties",
        "spécialité": "specialty",
        "spécialités": "specialties",
        "généralité": "generality",
        "généralités": "generalities",
        "particularité": "particularity",
        "particularités": "particularities"
    }

    # Apply translations (case insensitive with proper case handling)
    result = text
    for french, english in translations.items():
        # Create a more comprehensive pattern that handles case variations
        def replace_match(match):
            matched_text = match.group(0)
            if matched_text.isupper():
                return english.upper()
            elif matched_text.istitle() or matched_text[0].isupper():
                return english.capitalize()
            else:
                return english.lower()

        # Replace whole words only, case insensitive
        pattern = r'\b' + re.escape(french) + r'\b'
        result = re.sub(pattern, replace_match, result, flags=re.IGNORECASE)

    return result

def translate_keywords(keywords: str) -> str:
    """Translate keywords specifically, handling numbered lists and separators."""
    if not keywords or pd.isna(keywords):
        return keywords

    # Split on common separators and translate each part
    parts = re.split(r'[,;]\s*|\n\d+\.\s*', keywords)
    translated_parts = []

    for part in parts:
        if part.strip():
            translated = translate_text(part.strip())
            translated_parts.append(translated)

    return ', '.join(translated_parts)

def translate_theme(theme: str) -> str:
    """Translate theme field."""
    if not theme or pd.isna(theme):
        return theme

    return translate_text(theme)

def process_csv_translation():
    """Process the CSV file and translate French fields to English."""

    print("Loading CSV file...")
    csv_path = "/Users/murexpecten/Code/the-library/data/biblio/bibliographie_finale_these_FINAL!.csv"

    # First, analyze the entire CSV to count French content
    print("\n" + "="*80)
    print("ANALYZING CSV FOR FRENCH CONTENT...")
    print("="*80)

    df_full = pd.read_csv(csv_path)
    total_rows = len(df_full)

    french_summaries = 0
    french_keywords = 0
    french_themes = 0

    print(f"\nTotal rows in CSV: {total_rows}")

    # Count French summaries
    if 'summary' in df_full.columns:
        for idx, summary in df_full['summary'].items():
            if pd.notna(summary) and str(summary).strip() and not is_mostly_english(str(summary)):
                french_summaries += 1

    # Count French keywords
    if 'keywords' in df_full.columns:
        for idx, keywords in df_full['keywords'].items():
            if pd.notna(keywords) and str(keywords).strip() and not is_mostly_english(str(keywords)):
                french_keywords += 1

    # Count French themes
    if 'theme' in df_full.columns:
        for idx, theme in df_full['theme'].items():
            if pd.notna(theme) and str(theme).strip() and not is_mostly_english(str(theme)):
                french_themes += 1

    print(f"\n📊 FRENCH CONTENT DETECTED:")
    print(f"  • Summaries in French: {french_summaries:,} / {total_rows:,} ({french_summaries*100/total_rows:.1f}%)")
    print(f"  • Keywords in French: {french_keywords:,} / {total_rows:,} ({french_keywords*100/total_rows:.1f}%)")
    print(f"  • Themes in French: {french_themes:,} / {total_rows:,} ({french_themes*100/total_rows:.1f}%)")

    estimated_translations = french_summaries + french_keywords + french_themes
    print(f"\n⏱️  Estimated translations needed: ~{estimated_translations:,}")
    print(f"   (Summaries will use neural translation, keywords/themes use pattern matching)")

    print("\n" + "="*80)
    print("STARTING TRANSLATION PROCESS...")
    print("="*80)

    # Initialize translation model
    init_translation_model()

    # Read CSV in chunks to handle large file
    chunk_size = 100  # Smaller chunks for neural translation
    chunks = []
    rows_processed = 0

    for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
        rows_processed += len(chunk)
        print(f"\n--- Processing chunk: rows {rows_processed - len(chunk) + 1} to {rows_processed} of {total_rows} ---")

        # Translate summary field using neural model
        if 'summary' in chunk.columns:
            print("Checking summaries for French content...")
            chunk['summary'] = chunk['summary'].apply(lambda x: translate_with_model(x) if pd.notna(x) and str(x).strip() else x)

        # Translate keywords field using pattern matching
        if 'keywords' in chunk.columns:
            print("Translating keywords (pattern matching)...")
            translated_keywords = chunk['keywords'].apply(translate_keywords)
            chunk['keywords'] = translated_keywords
            if 'keywords_en' in chunk.columns:
                chunk['keywords_en'] = translated_keywords

        # Translate theme field using pattern matching
        if 'theme' in chunk.columns:
            print("Translating themes (pattern matching)...")
            translated_theme = chunk['theme'].apply(translate_theme)
            chunk['theme'] = translated_theme
            if 'theme_en' in chunk.columns:
                chunk['theme_en'] = translated_theme

        chunks.append(chunk)

    # Combine all chunks
    print("Combining chunks...")
    df = pd.concat(chunks, ignore_index=True)

    # Save the translated CSV
    output_path = "/Users/murexpecten/Code/the-library/data/biblio/bibliographie_finale_these_FINAL_translated.csv"
    print(f"Saving translated CSV to {output_path}...")
    df.to_csv(output_path, index=False)

    print(f"Translation complete! Processed {len(df)} rows.")
    print(f"Original file: {csv_path}")
    print(f"Translated file: {output_path}")

    # Show sample of translated content
    print("\nSample of translated content:")
    for i, row in df.head(3).iterrows():
        print(f"\nRow {i+1}:")
        print(f"Title: {row['title']}")
        if 'summary' in row and pd.notna(row['summary']):
            summary = str(row['summary'])[:200] + "..." if len(str(row['summary'])) > 200 else str(row['summary'])
            print(f"Summary: {summary}")
        if 'keywords' in row and pd.notna(row['keywords']):
            keywords = str(row['keywords'])[:150] + "..." if len(str(row['keywords'])) > 150 else str(row['keywords'])
            print(f"Keywords: {keywords}")
        if 'theme' in row and pd.notna(row['theme']):
            print(f"Theme: {row['theme']}")

if __name__ == "__main__":
    process_csv_translation()