from django.core.management.base import BaseCommand, CommandError

from sources.models import Source
from sources.pipeline import run_source, translate_published


class Command(BaseCommand):
    help = "Run due data sources, then translate newly published events into Persian."

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Run only the source with this adapter code, e.g. kultursanat")
        parser.add_argument("--force", action="store_true", help="Run even if the source is not due yet")
        parser.add_argument("--limit", type=int, help="Process at most this many event pages per source")
        parser.add_argument("--no-translate", action="store_true", help="Skip the translation step")

    def handle(self, *args, **opts):
        sources = Source.objects.all()
        if opts["source"]:
            sources = sources.filter(adapter=opts["source"])
            if not sources.exists():
                raise CommandError(f"Source '{opts['source']}' not found")

        for source in sources:
            if not source.can_run():
                self.stdout.write(f"- {source}: skipped (inactive or terms not allowed)")
                continue
            if not (opts["force"] or source.is_due()):
                self.stdout.write(f"- {source}: not due yet")
                continue
            run = run_source(source, limit=opts["limit"])
            line = (
                f"- {source}: links={run.links_found} new={run.created} updated={run.updated} "
                f"unchanged={run.unchanged} review={run.sent_to_review} failed={run.failed}"
            )
            self.stdout.write(self.style.ERROR(line + f"\n  error: {run.error}") if run.error else self.style.SUCCESS(line))

        if not opts["no_translate"]:
            self.stdout.write(f"Translated {translate_published()} events.")
