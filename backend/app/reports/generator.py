from datetime import datetime
from pathlib import Path

import structlog
from bson import ObjectId
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings
from app.db.models import ReportBase, TestResultInDB, TestRunInDB
from app.db.repositories import report_repository, result_repository, run_repository

logger = structlog.get_logger()


class ReportGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.reports_dir = Path(self.settings.reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        templates_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def generate(self, run_id: ObjectId, user_id: ObjectId, format: str = "html") -> None:
        run = await run_repository.get_by_id(run_id, user_id)
        if not run:
            logger.error("Run not found for report", run_id=str(run_id))
            return

        results = await result_repository.list_by_run(run_id, limit=10000)
        spec = run.spec_id

        html_path = None
        pdf_path = None

        if format in ("html", "both"):
            html_path = await self._generate_html(run, results, spec)

        if format in ("pdf", "both"):
            if html_path:
                pdf_path = await self._generate_pdf(html_path, run)
            else:
                html_path = await self._generate_html(run, results, spec)
                pdf_path = await self._generate_pdf(html_path, run)

        file_size = 0
        if html_path and Path(html_path).exists():
            file_size += Path(html_path).stat().st_size
        if pdf_path and Path(pdf_path).exists():
            file_size += Path(pdf_path).stat().st_size

        report_base = ReportBase(run_id=run_id, user_id=user_id, format=format)
        await report_repository.create(report_base, html_path=html_path, pdf_path=pdf_path)

        logger.info("Report generated", run_id=str(run_id), html=html_path, pdf=pdf_path)

    async def _generate_html(self, run: TestRunInDB, results: list[TestResultInDB], spec_id: ObjectId) -> str:
        template = self.jinja_env.get_template("report.html")

        summary = {
            "total": run.summary.total,
            "passed": run.summary.passed,
            "failed": run.summary.failed,
            "errors": run.summary.errors,
            "skipped": run.summary.skipped,
            "duration_seconds": run.summary.duration_seconds,
            "pass_rate": (run.summary.passed / run.summary.total * 100) if run.summary.total > 0 else 0,
        }

        results_by_category = {}
        for r in results:
            cat = r.category
            if cat not in results_by_category:
                results_by_category[cat] = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "details": []}
            results_by_category[cat]["details"].append(r)
            if r.status == "passed":
                results_by_category[cat]["passed"] += 1
            elif r.status == "failed":
                results_by_category[cat]["failed"] += 1
            elif r.status == "error":
                results_by_category[cat]["errors"] += 1
            elif r.status == "skipped":
                results_by_category[cat]["skipped"] += 1

        html = template.render(
            run=run,
            summary=summary,
            results_by_category=results_by_category,
            disclaimer=self.settings.report_disclaimer,
            generated_at=datetime.now().isoformat(),
        )

        filename = f"run_{run.id}.html"
        filepath = self.reports_dir / filename
        filepath.write_text(html, encoding="utf-8")
        return str(filepath)

    async def _generate_pdf(self, html_path: str, run: TestRunInDB) -> str:
        try:
            from weasyprint import CSS, HTML
        except (ImportError, OSError) as e:
            logger.warning(
                "WeasyPrint (PDF generation) is unavailable. Install GTK libraries for Windows to enable PDF generation.",
                error=str(e),
            )
            return ""

        pdf_filename = f"run_{run.id}.pdf"
        pdf_path = self.reports_dir / pdf_filename

        css_path = Path(__file__).parent / "styles" / "report.css"
        css = CSS(filename=str(css_path)) if css_path.exists() else None

        html_doc = HTML(filename=html_path)
        html_doc.write_pdf(str(pdf_path), stylesheets=[css] if css else None)

        return str(pdf_path)
