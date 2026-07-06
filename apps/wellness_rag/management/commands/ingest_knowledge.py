"""
Usage:
    python manage.py ingest_knowledge path/to/chunks.json

Expects a JSON file: a list of {"id", "text", "source_url", "source_name"}
objects. Scrape + chunk your own WHO/NHS/PubMed content (~200-400 tokens
per chunk) into this shape, then run this command to embed and store it.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from apps.wellness_rag.vector_store import ingest_chunks


class Command(BaseCommand):
    help = "Ingest a JSON file of scraped+chunked knowledge into the public vector store"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)
        parser.add_argument("--batch-size", type=int, default=50)

    def handle(self, *args, **options):
        path = options["json_path"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")

        if not isinstance(chunks, list):
            raise CommandError("JSON file must contain a list of chunk objects")

        batch_size = options["batch_size"]
        total = len(chunks)
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            ingest_chunks(batch)
            self.stdout.write(f"Ingested {min(i + batch_size, total)}/{total} chunks")

        self.stdout.write(self.style.SUCCESS(f"Done. Ingested {total} chunks total."))