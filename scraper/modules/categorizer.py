"""Contact categorization and platform routing module."""

from datetime import datetime

# Category detection rules: keywords + source type scoring
CATEGORY_RULES = {
    "avocat": {
        "keywords": [
            "avocat", "lawyer", "attorney", "abogado", "law firm",
            "cabinet juridique", "legal", "barrister", "solicitor",
            "droit", "juridique", "rechtsanwalt", "advokat",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "assureur": {
        "keywords": [
            "assureur", "insurance", "assurance", "broker", "courtier",
            "axa", "allianz", "april", "expat insurance", "health insurance",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "notaire": {
        "keywords": [
            "notaire", "notary", "notario", "notarial",
        ],
        "sources": ["google_maps", "google_search"],
    },
    "medecin": {
        "keywords": [
            "medecin", "doctor", "clinic", "clinique", "hopital",
            "hospital", "dentist", "dentiste", "health", "sante",
            "generaliste", "specialiste", "chirurgien", "surgeon",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "comptable": {
        "keywords": [
            "comptable", "accountant", "accounting", "comptabilite",
            "expert-comptable", "expert comptable", "bookkeeper",
            "cabinet comptable", "fiscal", "fiscaliste", "tax advisor",
            "steuerberater", "buchhalter",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "traducteur": {
        "keywords": [
            "traducteur", "translator", "traduction", "translation",
            "interprete", "interpreter", "sworn translator",
            "traducteur assermente", "certified translator",
            "bureau de traduction", "translation agency",
            "ubersetzer", "traductor",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "agent_immo": {
        "keywords": [
            "agent immobilier", "real estate", "immobilier", "realtor",
            "agence immobiliere", "property", "estate agent",
            "relocation", "relocation agent", "housing",
            "makler", "inmobiliaria",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "demenageur": {
        "keywords": [
            "demenageur", "demenagement", "moving company", "mover",
            "international moving", "relocation", "demenagement international",
            "removals", "umzug", "mudanza",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "banquier": {
        "keywords": [
            "banquier", "banker", "banque", "bank", "private banking",
            "gestion patrimoine", "wealth management", "conseiller bancaire",
            "financial advisor", "conseiller financier",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "consultant": {
        "keywords": [
            "consultant", "consulting", "conseil", "advisory",
            "cabinet conseil", "consulting firm", "strategy",
            "consultant expatriation", "mobility consultant",
        ],
        "sources": ["google_maps", "google_search", "custom_urls"],
    },
    "blogueur": {
        "keywords": [
            "blog", "blogueur", "blogger", "travel blog", "voyage",
            "expat blog", "digital nomad", "nomade",
        ],
        "sources": ["google_search", "custom_urls"],
    },
    "influenceur": {
        "keywords": [
            "influenceur", "influencer", "content creator",
            "createur contenu", "social media",
        ],
        "sources": ["google_search", "custom_urls"],
    },
    "youtubeur": {
        "keywords": [
            "youtubeur", "youtuber", "youtube", "chaine youtube",
            "youtube channel", "vlogger", "vlog",
        ],
        "sources": ["google_search", "custom_urls"],
    },
    "admin_groupe": {
        "keywords": [
            "admin", "administrator", "moderator", "groupe",
            "group", "community", "communaute", "facebook group",
        ],
        "sources": ["google_search", "custom_urls"],
    },
}

# Platform routing
SOS_EXPAT_CATEGORIES = {
    "avocat", "assureur", "notaire", "medecin", "comptable",
    "traducteur", "agent_immo", "demenageur", "banquier", "consultant",
}
ULIXAI_CATEGORIES = {"blogueur", "influenceur", "admin_groupe", "youtubeur"}


def categorize(contact: dict) -> str:
    """
    Determine category of a contact based on keywords and source.
    Returns category string or 'autre'.
    """
    text_to_analyze = " ".join([
        contact.get("keywords", "") or "",
        contact.get("name", "") or "",
        contact.get("website", "") or "",
        contact.get("source_url", "") or "",
    ]).lower()

    scores = {}
    for category, rules in CATEGORY_RULES.items():
        score = 0
        for keyword in rules["keywords"]:
            if keyword in text_to_analyze:
                score += 10
        if contact.get("source_type") in rules["sources"]:
            score += 5
        scores[category] = score

    if not scores or max(scores.values()) < 10:
        return "autre"

    return max(scores, key=scores.get)


def determine_platform(category: str) -> str:
    """Determine target platform based on category."""
    if category in SOS_EXPAT_CATEGORIES:
        return "sos-expat"
    elif category in ULIXAI_CATEGORIES:
        return "ulixai"
    else:
        return "sos-expat"  # Default


def generate_tags(contact: dict, category: str) -> list[str]:
    """Generate automatic tags for a contact."""
    now = datetime.now()
    tags = [
        category,
        contact.get("source_type", ""),
        f"{now.year}-{now.month:02d}",
    ]

    country = contact.get("country")
    if country:
        tags.append(country.upper())

    # Custom tags from job config
    job_tags = contact.get("job_tags")
    if job_tags and isinstance(job_tags, list):
        tags.extend(job_tags)

    # Deduplicate and clean
    return list({t.strip().lower() for t in tags if t and t.strip()})
