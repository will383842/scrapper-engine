"""
Cron job: Process pending scraped contacts.
Runs every hour. Validates, categorizes, routes to MailWizz lists.
"""

import json
import logging
import sys

from scraper.database import get_db_session
from scraper.modules.validator import validate_email, validate_phone, clean_phone
from scraper.modules.categorizer import categorize, determine_platform, generate_tags
from scraper.modules.router import get_routing_info

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("process_contacts")

BATCH_SIZE = 1000


def process_pending_contacts():
    """Process all contacts with status 'pending_validation'."""
    stats = {"processed": 0, "validated": 0, "rejected": 0, "duplicates": 0}

    with get_db_session() as session:
        # Fetch pending contacts
        result = session.execute(
            """
            SELECT * FROM scraped_contacts
            WHERE status = 'pending_validation'
            ORDER BY scraped_at ASC
            LIMIT :limit
            """,
            {"limit": BATCH_SIZE},
        )
        contacts = result.mappings().all()

        logger.info(f"Processing {len(contacts)} pending contacts...")

        for contact in contacts:
            stats["processed"] += 1
            contact = dict(contact)

            # 1. Validate email
            if not validate_email(contact.get("email", "")):
                session.execute(
                    """
                    UPDATE scraped_contacts
                    SET status = 'rejected', processed_at = NOW()
                    WHERE id = :id
                    """,
                    {"id": contact["id"]},
                )
                stats["rejected"] += 1
                continue

            # 2. Check duplicate in validated_contacts
            existing = session.execute(
                "SELECT id FROM validated_contacts WHERE email = :email",
                {"email": contact["email"].lower()},
            ).first()

            if existing:
                session.execute(
                    """
                    UPDATE scraped_contacts
                    SET status = 'rejected', processed_at = NOW()
                    WHERE id = :id
                    """,
                    {"id": contact["id"]},
                )
                stats["duplicates"] += 1
                continue

            # 3. Check email domain blacklist
            domain = contact["email"].split("@")[1]
            blacklisted = session.execute(
                "SELECT id FROM email_domain_blacklist WHERE domain = :domain",
                {"domain": domain},
            ).first()

            if blacklisted:
                session.execute(
                    """
                    UPDATE scraped_contacts
                    SET status = 'rejected', processed_at = NOW()
                    WHERE id = :id
                    """,
                    {"id": contact["id"]},
                )
                stats["rejected"] += 1
                continue

            # 4. Categorize
            category = categorize(contact)

            # 5. Determine platform
            platform = determine_platform(category)

            # 6. Generate tags
            tags = generate_tags(contact, category)

            # 7. Get MailWizz routing
            routing = get_routing_info(category, platform)

            # 8. Insert validated contact
            session.execute(
                """
                INSERT INTO validated_contacts
                    (email, name, phone, website, address, social_media,
                     category, platform, country, tags,
                     email_valid, phone_valid,
                     mailwizz_list_id, mailwizz_template,
                     source_id, status)
                VALUES
                    (:email, :name, :phone, :website, :address, :social_media,
                     :category, :platform, :country, :tags,
                     TRUE, :phone_valid,
                     :list_id, :template,
                     :source_id, 'ready_for_mailwizz')
                ON CONFLICT (email) DO NOTHING
                """,
                {
                    "email": contact["email"].lower(),
                    "name": contact.get("name"),
                    "phone": clean_phone(contact.get("phone")),
                    "website": contact.get("website"),
                    "address": contact.get("address"),
                    "social_media": contact.get("social_media", "{}"),
                    "category": category,
                    "platform": platform,
                    "country": contact.get("country"),
                    "tags": json.dumps(tags),
                    "phone_valid": validate_phone(
                        contact.get("phone"), contact.get("country")
                    ),
                    "list_id": routing["list_id"],
                    "template": routing.get("template_default"),
                    "source_id": contact["id"],
                },
            )

            # 9. Update scraped contact status
            session.execute(
                """
                UPDATE scraped_contacts
                SET status = 'validated', processed_at = NOW()
                WHERE id = :id
                """,
                {"id": contact["id"]},
            )

            stats["validated"] += 1
            logger.info(
                f"Validated: {contact['email']} -> {category} -> "
                f"{platform} (list #{routing['list_id']})"
            )

    logger.info(f"Processing complete: {stats}")
    return stats


if __name__ == "__main__":
    process_pending_contacts()
