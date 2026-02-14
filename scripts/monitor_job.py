#!/usr/bin/env python3
"""
Monitor Scraping Job - Surveillance temps réel
================================================

Usage:
    python monitor_job.py <job_id> [--interval SECONDS] [--api-url URL]

Exemples:
    python monitor_job.py 123
    python monitor_job.py 123 --interval 5
    python monitor_job.py 123 --api-url http://api.example.com:8000

Dépendances:
    pip install requests rich
"""

import argparse
import sys
import time
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ Erreur: 'requests' n'est pas installé")
    print("   Installation: pip install requests")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.live import Live
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Attention: 'rich' n'est pas installé (affichage limité)")
    print("   Installation: pip install rich")
    print()


class JobMonitor:
    def __init__(self, job_id: int, api_url: str = "http://localhost:8000", interval: int = 10):
        self.job_id = job_id
        self.api_url = api_url.rstrip("/")
        self.interval = interval
        self.status_url = f"{self.api_url}/api/v1/scraping/jobs/{job_id}/status"
        self.logs_url = f"{self.api_url}/api/v1/scraping/jobs/{job_id}/logs"
        self.console = Console() if RICH_AVAILABLE else None
        self.iteration = 0

    def fetch_status(self) -> Optional[dict]:
        """Récupère le status du job."""
        try:
            response = requests.get(self.status_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if self.console:
                self.console.print(f"[red]❌ Erreur API: {e}[/red]")
            else:
                print(f"❌ Erreur API: {e}")
            return None

    def fetch_logs(self, limit: int = 5) -> Optional[dict]:
        """Récupère les logs récents."""
        try:
            response = requests.get(f"{self.logs_url}?limit={limit}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def display_status_rich(self, data: dict):
        """Affichage enrichi avec Rich."""
        status = data.get("status", "N/A")
        progress = data.get("progress", 0)
        pages = data.get("pages_scraped", 0)
        contacts = data.get("contacts_extracted", 0)
        errors = data.get("errors_count", 0)
        name = data.get("name", "N/A")
        source_type = data.get("source_type", "N/A")

        # Couleur selon le status
        status_colors = {
            "running": "yellow",
            "completed": "green",
            "failed": "red",
            "pending": "cyan",
            "paused": "magenta",
        }
        status_emojis = {
            "running": "⚙️",
            "completed": "✅",
            "failed": "❌",
            "pending": "⏳",
            "paused": "⏸️",
        }
        status_color = status_colors.get(status, "white")
        status_emoji = status_emojis.get(status, "❓")

        # Créer un tableau
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")

        table.add_row("Job ID", f"#{self.job_id}")
        table.add_row("Name", name)
        table.add_row("Status", f"[{status_color}]{status_emoji} {status.upper()}[/{status_color}]")
        table.add_row("Progress", f"{progress:.1f}%")
        table.add_row("Type", source_type)
        table.add_row("Pages Scraped", str(pages))
        table.add_row("Contacts", str(contacts))

        if errors > 0:
            table.add_row("Errors", f"[red]{errors} ⚠️[/red]")
        else:
            table.add_row("Errors", str(errors))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        panel = Panel(
            table,
            title=f"[bold]Monitoring Job #{self.job_id}[/bold]",
            subtitle=f"Refresh #{self.iteration} | {timestamp}",
            border_style=status_color,
        )

        self.console.clear()
        self.console.print(panel)

        # Afficher un lien vers les logs si erreurs
        if errors > 0:
            self.console.print(f"\n[yellow]⚠️  Logs disponibles:[/yellow] {self.logs_url}")

    def display_status_simple(self, data: dict):
        """Affichage simple sans Rich."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Rafraîchissement #{self.iteration}")
        print("━" * 60)
        print(f"  Job ID      : #{self.job_id}")
        print(f"  Name        : {data.get('name', 'N/A')}")
        print(f"  Status      : {data.get('status', 'N/A').upper()}")
        print(f"  Progress    : {data.get('progress', 0):.1f}%")
        print(f"  Type        : {data.get('source_type', 'N/A')}")
        print(f"  Pages       : {data.get('pages_scraped', 0)}")
        print(f"  Contacts    : {data.get('contacts_extracted', 0)}")
        print(f"  Errors      : {data.get('errors_count', 0)}")
        print("━" * 60)

    def display_final_summary(self, data: dict):
        """Affiche le résumé final."""
        status = data.get("status", "N/A")
        pages = data.get("pages_scraped", 0)
        contacts = data.get("contacts_extracted", 0)
        errors = data.get("errors_count", 0)

        if self.console:
            self.console.print("\n[bold]🏁 Job Terminé[/bold]")
            self.console.print(f"Status final: [{status}]")
            self.console.print("\n[bold]📊 Résumé:[/bold]")
            self.console.print(f"  • Pages scrapées    : {pages}")
            self.console.print(f"  • Contacts extraits : {contacts}")
            self.console.print(f"  • Erreurs           : {errors}")

            if status == "completed" and errors > 0:
                self.console.print(f"\n[yellow]⚠️  Des erreurs ont été détectées:[/yellow]")
                self.console.print(f"   curl {self.logs_url}")
            elif status == "failed":
                self.console.print(f"\n[red]❌ Le job a échoué. Consultez les logs:[/red]")
                self.console.print(f"   curl {self.logs_url} | jq '.logs[]'")
        else:
            print("\n🏁 Job Terminé")
            print(f"Status final: {status}")
            print(f"\n📊 Résumé:")
            print(f"  • Pages scrapées    : {pages}")
            print(f"  • Contacts extraits : {contacts}")
            print(f"  • Erreurs           : {errors}")

            if errors > 0:
                print(f"\n⚠️  Consultez les logs: {self.logs_url}")

    def run(self):
        """Lance la surveillance."""
        if self.console:
            self.console.print(f"\n[bold cyan]🔍 Vérification du job #{self.job_id}...[/bold cyan]")
        else:
            print(f"\n🔍 Vérification du job #{self.job_id}...")

        # Vérifier que le job existe
        data = self.fetch_status()
        if not data:
            if self.console:
                self.console.print(f"[red]❌ Job #{self.job_id} introuvable[/red]")
            else:
                print(f"❌ Job #{self.job_id} introuvable")
            sys.exit(1)

        job_name = data.get("name", "N/A")
        if self.console:
            self.console.print(f"[green]✅ Job trouvé: {job_name}[/green]")
            self.console.print(f"\n[dim]Surveillance toutes les {self.interval}s (Ctrl+C pour arrêter)[/dim]\n")
        else:
            print(f"✅ Job trouvé: {job_name}")
            print(f"\nSurveillance toutes les {self.interval}s (Ctrl+C pour arrêter)\n")

        try:
            while True:
                self.iteration += 1
                data = self.fetch_status()

                if not data:
                    time.sleep(self.interval)
                    continue

                # Afficher le status
                if RICH_AVAILABLE:
                    self.display_status_rich(data)
                else:
                    self.display_status_simple(data)

                # Vérifier si terminé
                status = data.get("status", "")
                if status in ["completed", "failed", "cancelled"]:
                    self.display_final_summary(data)
                    break

                time.sleep(self.interval)

        except KeyboardInterrupt:
            if self.console:
                self.console.print("\n\n[yellow]⏹️  Surveillance interrompue[/yellow]")
            else:
                print("\n\n⏹️  Surveillance interrompue")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Surveiller un job de scraping en temps réel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s 123                              Surveiller le job #123
  %(prog)s 123 --interval 5                 Rafraîchir toutes les 5 secondes
  %(prog)s 123 --api-url http://prod:8000   API distante

Dépendances optionnelles:
  pip install rich    (affichage enrichi)
        """
    )
    parser.add_argument("job_id", type=int, help="ID du job à surveiller")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=10,
        help="Intervalle de rafraîchissement en secondes (défaut: 10)"
    )
    parser.add_argument(
        "--api-url",
        "-u",
        default="http://localhost:8000",
        help="URL de l'API (défaut: http://localhost:8000)"
    )

    args = parser.parse_args()

    monitor = JobMonitor(
        job_id=args.job_id,
        api_url=args.api_url,
        interval=args.interval
    )
    monitor.run()


if __name__ == "__main__":
    main()
