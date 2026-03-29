"""Reporting and visualization services."""

from __future__ import annotations

import csv
from io import BytesIO, StringIO
from statistics import mean
from typing import Any

import networkx as nx

from app.evaluation.plagiarism import SimilarityEdge
from app.models.academic import Experiment
from app.models.enums import SimilarityLevel
from app.schemas.report import ExperimentReportSummary, ReportArtifact
from app.schemas.result import PlagiarismNetworkResponse, ResultRead
from app.storage.service import get_storage_provider
from app.utils.config import get_settings

settings = get_settings()


class ReportService:
    """Generate CSV, PDF, dashboard, and network artifacts."""

    @staticmethod
    def _simple_pdf_bytes(lines: list[str]) -> bytes:
        """Generate a minimal PDF document without external dependencies."""

        def escape(value: str) -> str:
            return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        text_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
        for line in lines:
            text_lines.append(f"({escape(line)}) Tj")
            text_lines.append("T*")
        text_lines.append("ET")
        content = "\n".join(text_lines).encode("latin-1", errors="replace")

        objects = [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
            f"4 0 obj << /Length {len(content)} >> stream\n".encode("latin-1") + content + b"\nendstream endobj",
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        ]

        buffer = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(buffer))
            buffer.extend(obj)
            buffer.extend(b"\n")

        xref_offset = len(buffer)
        buffer.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        buffer.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        buffer.extend(
            (
                f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF"
            ).encode("latin-1")
        )
        return bytes(buffer)

    @staticmethod
    def reconstruct_edges(rows: list[ResultRead]) -> list[SimilarityEdge]:
        """Rebuild plagiarism edges from persisted result breakdowns."""
        merged: dict[tuple[str, str], SimilarityEdge] = {}
        for row in rows:
            for match in row.breakdown.get("plagiarism_matches", []):
                peer_id = match.get("peer_submission_id")
                if not peer_id:
                    continue
                key = tuple(sorted((row.submission_id, peer_id)))
                candidate = SimilarityEdge(
                    source_submission_id=key[0],
                    target_submission_id=key[1],
                    tfidf_score=float(match.get("tfidf_score", 0.0)),
                    ngram_score=float(match.get("ngram_score", 0.0)),
                    semantic_score=float(match.get("semantic_score", 0.0)),
                    combined_score=float(match.get("combined_score", 0.0)),
                )
                existing = merged.get(key)
                if existing is None or candidate.combined_score > existing.combined_score:
                    merged[key] = candidate
        return list(merged.values())

    @staticmethod
    def _report_prefix(experiment_id: str) -> str:
        return f"reports/experiment_{experiment_id}"

    @staticmethod
    def _artifact(name: str, relative_path: str) -> ReportArtifact:
        storage = get_storage_provider()
        return ReportArtifact(
            name=name,
            relative_path=relative_path,
            absolute_path=str(storage.resolve_path(relative_path)),
        )

    @staticmethod
    def _compute_top_sources(graph: nx.Graph) -> list[dict[str, Any]]:
        weighted_scores: list[tuple[str, float]] = []
        for node in graph.nodes:
            score = sum(float(edge_data.get("weight", 0.0)) for _, _, edge_data in graph.edges(node, data=True))
            weighted_scores.append((node, score))

        return [
            {
                "submission_id": submission_id,
                "submitter_label": graph.nodes[submission_id].get("label"),
                "filename": graph.nodes[submission_id].get("filename"),
                "score": round(score, 4),
            }
            for submission_id, score in sorted(weighted_scores, key=lambda item: item[1], reverse=True)[:5]
        ]

    @staticmethod
    def generate_network_graph(
        experiment: Experiment,
        submission_lookup: dict[str, dict[str, str]],
        edges: list[SimilarityEdge],
    ) -> tuple[PlagiarismNetworkResponse, ReportArtifact | None]:
        """Build the plagiarism network and save it as HTML."""
        graph = nx.Graph()
        for submission_id, metadata in submission_lookup.items():
            graph.add_node(
                submission_id,
                label=metadata["label"],
                filename=metadata.get("filename"),
            )

        edge_payloads: list[dict[str, Any]] = []
        for edge in edges:
            if edge.combined_score < settings.plagiarism_threshold_low:
                continue

            graph.add_edge(
                edge.source_submission_id,
                edge.target_submission_id,
                weight=edge.combined_score,
            )
            edge_payloads.append(
                {
                    "source": edge.source_submission_id,
                    "target": edge.target_submission_id,
                    "score": edge.combined_score,
                    "tfidf_score": edge.tfidf_score,
                    "ngram_score": edge.ngram_score,
                    "semantic_score": edge.semantic_score,
                }
            )

        cluster_count = sum(1 for component in nx.connected_components(graph) if len(component) > 1)
        top_sources = ReportService._compute_top_sources(graph)

        if graph.number_of_nodes() == 0:
            return (
                PlagiarismNetworkResponse(
                    experiment_id=experiment.id,
                    html_relative_path=None,
                    node_count=0,
                    edge_count=0,
                    cluster_count=0,
                    nodes=[],
                    edges=[],
                    top_sources=[],
                ),
                None,
            )

        html_relative_path: str | None = None
        artifact: ReportArtifact | None = None
        try:
            from pyvis.network import Network

            network = Network(height="760px", width="100%", bgcolor="#ffffff", font_color="#0f172a")
            for node_id, metadata in graph.nodes(data=True):
                network.add_node(
                    node_id,
                    label=metadata.get("label", node_id),
                    title=f"{metadata.get('label', '')}<br>{metadata.get('filename', '')}",
                    color="#d97706" if graph.degree(node_id) > 0 else "#0f766e",
                )
            for source, target, metadata in graph.edges(data=True):
                network.add_edge(source, target, value=float(metadata.get("weight", 0.0)) * 10)

            html = network.generate_html()
            html_relative_path = f"{ReportService._report_prefix(experiment.id)}/plagiarism_network.html"
            storage_artifact = get_storage_provider().save_bytes(html_relative_path, html.encode("utf-8"))
            artifact = ReportArtifact(
                name="plagiarism_network_html",
                relative_path=storage_artifact.relative_path,
                absolute_path=str(storage_artifact.absolute_path),
            )
        except Exception:
            html_relative_path = None

        network_response = PlagiarismNetworkResponse(
            experiment_id=experiment.id,
            html_relative_path=html_relative_path,
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
            cluster_count=cluster_count,
            nodes=[
                {
                    "id": submission_id,
                    "submitter_label": metadata["label"],
                    "filename": metadata.get("filename"),
                }
                for submission_id, metadata in graph.nodes(data=True)
            ],
            edges=edge_payloads,
            top_sources=top_sources,
        )
        return network_response, artifact

    @staticmethod
    def generate_marks_csv(experiment: Experiment, rows: list[ResultRead]) -> ReportArtifact:
        """Generate CSV marksheet."""
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "Submitter",
                "Filename",
                "Score (/5)",
                "Plagiarism Score",
                "Plagiarism Level",
                "Top Classmate Similarity",
                "AI Generated Score",
                "AI Generated Level",
                "Relevance",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.submitter_label,
                    row.filename,
                    row.score_out_of_5,
                    row.plagiarism_score,
                    row.plagiarism_level.value,
                    row.top_classmate_similarity,
                    row.ai_generated_score,
                    row.ai_generated_level.value,
                    row.relevance_score,
                ]
            )

        relative_path = f"{ReportService._report_prefix(experiment.id)}/marks.csv"
        artifact = get_storage_provider().save_bytes(relative_path, buffer.getvalue().encode("utf-8"))
        return ReportArtifact(
            name="marks_csv",
            relative_path=artifact.relative_path,
            absolute_path=str(artifact.absolute_path),
        )

    @staticmethod
    def generate_summary_pdf(
        experiment: Experiment,
        rows: list[ResultRead],
        cluster_count: int,
        top_sources: list[dict[str, Any]],
    ) -> ReportArtifact:
        """Generate a simple PDF compliance report."""
        average_marks = round(mean([row.marks for row in rows]), 2) if rows else 0.0
        high_count = sum(1 for row in rows if row.plagiarism_level == SimilarityLevel.HIGH)
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

            buffer = BytesIO()
            document = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()

            story = [
                Paragraph("Academic Integrity Evaluation Report", styles["Title"]),
                Spacer(1, 12),
                Paragraph(f"Experiment: {experiment.topic}", styles["Heading2"]),
                Paragraph(f"Submission Count: {len(rows)}", styles["BodyText"]),
                Paragraph(f"Average Score (/5): {average_marks}", styles["BodyText"]),
                Paragraph(f"High-Risk Plagiarism Cases: {high_count}", styles["BodyText"]),
                Paragraph(f"Copy Clusters Detected: {cluster_count}", styles["BodyText"]),
                Spacer(1, 12),
            ]

            score_table = Table(
                [["Submitter", "Filename", "Score (/5)", "Plagiarism", "AI Risk", "Relevance"]]
                + [
                    [
                        row.submitter_label,
                        row.filename,
                        f"{row.score_out_of_5:.2f}",
                        f"{row.plagiarism_score:.2f} ({row.plagiarism_level.value})",
                        f"{row.ai_generated_score:.2f} ({row.ai_generated_level.value})",
                        f"{row.relevance_score:.2f}",
                    ]
                    for row in rows[:15]
                ]
            )
            score_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            story.extend([score_table, Spacer(1, 12)])

            if top_sources:
                story.append(Paragraph("Top Suspected Source Submissions", styles["Heading3"]))
                for source in top_sources:
                    story.append(
                        Paragraph(
                            f"{source.get('submitter_label', source['submission_id'])} | "
                            f"{source.get('filename', '')} | Score {source['score']}",
                            styles["BodyText"],
                        )
                    )

            document.build(story)
            pdf_bytes = buffer.getvalue()
        except Exception:
            lines = [
                "Academic Integrity Evaluation Report",
                f"Experiment: {experiment.topic}",
                f"Submission Count: {len(rows)}",
                f"Average Score (/5): {average_marks}",
                f"High-Risk Plagiarism Cases: {high_count}",
                f"Copy Clusters Detected: {cluster_count}",
                "",
                "Top Results:",
            ]
            for row in rows[:15]:
                lines.append(
                    f"{row.submitter_label} | {row.filename} | Score {row.score_out_of_5:.2f}/5 | "
                    f"Plagiarism {row.plagiarism_score:.2f} ({row.plagiarism_level.value}) | "
                    f"AI {row.ai_generated_score:.2f} ({row.ai_generated_level.value}) | "
                    f"Relevance {row.relevance_score:.2f}"
                )
            if top_sources:
                lines.append("")
                lines.append("Top Suspected Sources:")
                for source in top_sources:
                    lines.append(
                        f"{source.get('submitter_label', source['submission_id'])} | "
                        f"{source.get('filename', '')} | Score {source['score']}"
                    )
            pdf_bytes = ReportService._simple_pdf_bytes(lines)

        relative_path = f"{ReportService._report_prefix(experiment.id)}/summary_report.pdf"
        artifact = get_storage_provider().save_bytes(relative_path, pdf_bytes)
        return ReportArtifact(
            name="summary_pdf",
            relative_path=artifact.relative_path,
            absolute_path=str(artifact.absolute_path),
        )

    @staticmethod
    def generate_dashboard_html(experiment: Experiment, rows: list[ResultRead]) -> ReportArtifact | None:
        """Generate a Plotly dashboard page."""
        try:
            import plotly.graph_objects as go
        except Exception:
            return None

        marks = [row.marks for row in rows]
        plagiarism = [row.plagiarism_score for row in rows]
        relevance = [row.relevance_score for row in rows]

        histogram = go.Figure(
            data=[go.Histogram(x=marks, marker_color="#0f766e")],
            layout=go.Layout(title="Marks Distribution"),
        )
        scatter = go.Figure(
            data=[
                go.Scatter(
                    x=plagiarism,
                    y=relevance,
                    mode="markers+text",
                    text=[row.submitter_label for row in rows],
                    textposition="top center",
                    marker={"size": 10, "color": marks, "colorscale": "Viridis"},
                )
            ],
            layout=go.Layout(title="Plagiarism vs Relevance"),
        )

        html = """
        <html>
        <head><title>AIALES Dashboard</title></head>
        <body style="font-family:Segoe UI, sans-serif; background:#f8fafc;">
        <h1>Experiment Dashboard</h1>
        <h3>{topic}</h3>
        {histogram}
        <hr />
        {scatter}
        </body>
        </html>
        """.format(
            topic=experiment.topic,
            histogram=histogram.to_html(full_html=False, include_plotlyjs="cdn"),
            scatter=scatter.to_html(full_html=False, include_plotlyjs=False),
        )

        relative_path = f"{ReportService._report_prefix(experiment.id)}/dashboard.html"
        artifact = get_storage_provider().save_bytes(relative_path, html.encode("utf-8"))
        return ReportArtifact(
            name="dashboard_html",
            relative_path=artifact.relative_path,
            absolute_path=str(artifact.absolute_path),
        )

    @staticmethod
    def generate_report_bundle(
        experiment: Experiment,
        rows: list[ResultRead],
        submission_lookup: dict[str, dict[str, str]],
        edges: list[SimilarityEdge],
    ) -> tuple[ExperimentReportSummary, PlagiarismNetworkResponse]:
        """Generate all configured report artifacts."""
        average_marks = round(mean([row.marks for row in rows]), 2) if rows else 0.0
        high_count = sum(1 for row in rows if row.plagiarism_level == SimilarityLevel.HIGH)

        network_response, network_artifact = ReportService.generate_network_graph(
            experiment=experiment,
            submission_lookup=submission_lookup,
            edges=edges,
        )
        artifacts = [
            ReportService.generate_marks_csv(experiment, rows),
            ReportService.generate_summary_pdf(
                experiment=experiment,
                rows=rows,
                cluster_count=network_response.cluster_count,
                top_sources=network_response.top_sources,
            ),
        ]
        dashboard_artifact = ReportService.generate_dashboard_html(experiment, rows)
        if dashboard_artifact is not None:
            artifacts.append(dashboard_artifact)
        if network_artifact is not None:
            artifacts.append(network_artifact)

        summary = ExperimentReportSummary(
            experiment_id=experiment.id,
            average_marks=average_marks,
            submission_count=len(rows),
            plagiarism_high_count=high_count,
            cluster_count=network_response.cluster_count,
            top_sources=network_response.top_sources,
            artifacts=artifacts,
        )
        return summary, network_response
