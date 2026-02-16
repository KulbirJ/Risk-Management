"""Document parser service for extracting text from uploaded evidence files.

Supports: PDF, DOCX, XLSX/CSV, JSON, XML, plain text, and images.
Falls back gracefully if optional parsing libraries are not installed.
"""
import io
import json
import csv
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse uploaded documents and extract text content + metadata."""

    @staticmethod
    def parse(file_bytes: bytes, file_name: str, mime_type: str) -> dict:
        """
        Parse a document and return extracted text + metadata.
        
        Returns:
            {"text": str, "metadata": dict}
        """
        file_name_lower = file_name.lower()
        
        try:
            # Route by mime type / extension
            if mime_type == "application/pdf" or file_name_lower.endswith(".pdf"):
                return DocumentParser._parse_pdf(file_bytes, file_name)
            
            elif mime_type in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ) or file_name_lower.endswith(".docx"):
                return DocumentParser._parse_docx(file_bytes, file_name)
            
            elif mime_type in (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
            ) or file_name_lower.endswith((".xlsx", ".xls")):
                return DocumentParser._parse_xlsx(file_bytes, file_name)
            
            elif mime_type == "text/csv" or file_name_lower.endswith(".csv"):
                return DocumentParser._parse_csv(file_bytes, file_name)
            
            elif mime_type == "application/json" or file_name_lower.endswith(".json"):
                return DocumentParser._parse_json(file_bytes, file_name)
            
            elif mime_type in ("application/xml", "text/xml") or file_name_lower.endswith(".xml"):
                return DocumentParser._parse_xml(file_bytes, file_name)
            
            elif mime_type.startswith("text/") or file_name_lower.endswith((".txt", ".md", ".log", ".yml", ".yaml", ".ini", ".cfg", ".conf")):
                return DocumentParser._parse_text(file_bytes, file_name)
            
            elif mime_type.startswith("image/"):
                return DocumentParser._parse_image(file_bytes, file_name)
            
            else:
                # Try as text, fall back to binary info
                return DocumentParser._parse_text(file_bytes, file_name)

        except Exception as e:
            logger.error(f"Error parsing {file_name} ({mime_type}): {e}")
            return {
                "text": f"[Parsing failed for {file_name}: {str(e)}]",
                "metadata": {
                    "parser": "error",
                    "error": str(e),
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "size_bytes": len(file_bytes)
                }
            }

    @staticmethod
    def _parse_pdf(file_bytes: bytes, file_name: str) -> dict:
        """Extract text from PDF files."""
        try:
            import pdfplumber
        except ImportError:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                pages = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(text)
                
                full_text = "\n\n--- Page Break ---\n\n".join(pages)
                return {
                    "text": full_text,
                    "metadata": {
                        "parser": "PyPDF2",
                        "page_count": len(reader.pages),
                        "pages_with_text": len(pages),
                        "file_name": file_name,
                        "char_count": len(full_text)
                    }
                }
            except ImportError:
                return {
                    "text": f"[PDF file: {file_name} - PDF parsing libraries not installed. Install pypdf2 or pdfplumber.]",
                    "metadata": {"parser": "none", "file_name": file_name, "size_bytes": len(file_bytes)}
                }

        # Use pdfplumber (better table/text extraction)
        pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                # Also try to extract tables
                tables = page.extract_tables()
                table_text = ""
                for table in tables:
                    for row in table:
                        table_text += " | ".join(str(cell or "") for cell in row) + "\n"
                
                combined = text
                if table_text:
                    combined += f"\n[Table Data]\n{table_text}"
                if combined.strip():
                    pages.append(combined)

        full_text = "\n\n--- Page Break ---\n\n".join(pages)
        return {
            "text": full_text,
            "metadata": {
                "parser": "pdfplumber",
                "page_count": len(pages),
                "file_name": file_name,
                "char_count": len(full_text)
            }
        }

    @staticmethod
    def _parse_docx(file_bytes: bytes, file_name: str) -> dict:
        """Extract text from DOCX files."""
        try:
            from docx import Document
        except ImportError:
            return {
                "text": f"[DOCX file: {file_name} - python-docx not installed]",
                "metadata": {"parser": "none", "file_name": file_name, "size_bytes": len(file_bytes)}
            }

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                # Preserve heading structure
                if para.style and para.style.name and para.style.name.startswith("Heading"):
                    level = para.style.name.replace("Heading ", "").replace("Heading", "1")
                    try:
                        prefix = "#" * int(level)
                    except ValueError:
                        prefix = "#"
                    paragraphs.append(f"{prefix} {para.text}")
                else:
                    paragraphs.append(para.text)

        # Also extract tables
        table_texts = []
        for table in doc.tables:
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(" | ".join(cells))
            if rows:
                table_texts.append("\n".join(rows))

        full_text = "\n\n".join(paragraphs)
        if table_texts:
            full_text += "\n\n[Tables]\n" + "\n\n".join(table_texts)

        return {
            "text": full_text,
            "metadata": {
                "parser": "python-docx",
                "paragraph_count": len(paragraphs),
                "table_count": len(doc.tables),
                "file_name": file_name,
                "char_count": len(full_text)
            }
        }

    @staticmethod
    def _parse_xlsx(file_bytes: bytes, file_name: str) -> dict:
        """Extract text from Excel files."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            return {
                "text": f"[Excel file: {file_name} - openpyxl not installed]",
                "metadata": {"parser": "none", "file_name": file_name, "size_bytes": len(file_bytes)}
            }

        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        sheets_text = []
        total_rows = 0

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cell_values = [str(cell) if cell is not None else "" for cell in row]
                if any(v.strip() for v in cell_values):
                    rows.append(" | ".join(cell_values))
            
            if rows:
                total_rows += len(rows)
                sheet_text = f"[Sheet: {sheet_name}]\n" + "\n".join(rows)
                sheets_text.append(sheet_text)

        wb.close()
        full_text = "\n\n".join(sheets_text)

        return {
            "text": full_text,
            "metadata": {
                "parser": "openpyxl",
                "sheet_count": len(wb.sheetnames),
                "total_rows": total_rows,
                "file_name": file_name,
                "char_count": len(full_text)
            }
        }

    @staticmethod
    def _parse_csv(file_bytes: bytes, file_name: str) -> dict:
        """Extract text from CSV files."""
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = []
        for row in reader:
            rows.append(" | ".join(row))

        full_text = "\n".join(rows)
        return {
            "text": full_text,
            "metadata": {
                "parser": "csv",
                "row_count": len(rows),
                "file_name": file_name,
                "char_count": len(full_text)
            }
        }

    @staticmethod
    def _parse_json(file_bytes: bytes, file_name: str) -> dict:
        """Extract structured text from JSON files."""
        text = file_bytes.decode("utf-8", errors="replace")
        
        try:
            data = json.loads(text)
            # Pretty print for readability
            formatted = json.dumps(data, indent=2, default=str)
            
            # For large JSON, summarize structure
            metadata = {
                "parser": "json",
                "file_name": file_name,
                "char_count": len(formatted)
            }
            
            if isinstance(data, list):
                metadata["record_count"] = len(data)
                metadata["type"] = "array"
            elif isinstance(data, dict):
                metadata["top_level_keys"] = list(data.keys())[:20]
                metadata["type"] = "object"
            
            # Truncate very large JSON to keep within token limits
            if len(formatted) > 50000:
                formatted = formatted[:50000] + "\n... [truncated, full file has " + str(len(text)) + " chars]"
            
            return {"text": formatted, "metadata": metadata}

        except json.JSONDecodeError:
            return {"text": text[:50000], "metadata": {"parser": "json_raw", "file_name": file_name}}

    @staticmethod
    def _parse_xml(file_bytes: bytes, file_name: str) -> dict:
        """Extract text from XML files."""
        text = file_bytes.decode("utf-8", errors="replace")
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(text)
            
            # Extract all text content
            texts = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    texts.append(f"{tag}: {elem.text.strip()}")
                if elem.attrib:
                    for k, v in elem.attrib.items():
                        texts.append(f"  @{k}={v}")

            full_text = "\n".join(texts)
            return {
                "text": full_text if full_text else text[:50000],
                "metadata": {
                    "parser": "xml",
                    "root_tag": root.tag,
                    "element_count": sum(1 for _ in root.iter()),
                    "file_name": file_name,
                    "char_count": len(full_text)
                }
            }
        except Exception:
            # Fall back to raw XML text
            return {
                "text": text[:50000],
                "metadata": {"parser": "xml_raw", "file_name": file_name, "char_count": len(text)}
            }

    @staticmethod
    def _parse_text(file_bytes: bytes, file_name: str) -> dict:
        """Extract text from plain text files."""
        try:
            text = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            text = file_bytes.decode("latin-1", errors="replace")

        if len(text) > 50000:
            text = text[:50000] + f"\n... [truncated, full file has {len(file_bytes)} bytes]"

        return {
            "text": text,
            "metadata": {
                "parser": "text",
                "file_name": file_name,
                "char_count": len(text)
            }
        }

    @staticmethod
    def _parse_image(file_bytes: bytes, file_name: str) -> dict:
        """Handle image files - basic metadata extraction."""
        metadata = {
            "parser": "image",
            "file_name": file_name,
            "size_bytes": len(file_bytes)
        }

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            metadata["width"] = img.width
            metadata["height"] = img.height
            metadata["format"] = img.format
            metadata["mode"] = img.mode
        except ImportError:
            pass
        except Exception as e:
            metadata["error"] = str(e)

        return {
            "text": f"[Image file: {file_name}, size: {len(file_bytes)} bytes. Image content cannot be parsed as text. Consider using this as a visual reference.]",
            "metadata": metadata
        }

    @staticmethod
    def detect_document_type(text: str, file_name: str) -> str:
        """
        Auto-detect the document type based on content and filename.
        Returns: vulnerability_scan, architecture_doc, policy, network_diagram, config, other
        """
        text_lower = (text or "").lower()
        name_lower = file_name.lower()

        # Vulnerability scan indicators
        vuln_keywords = ["cve-", "cvss", "vulnerability", "exploit", "severity", "critical", "nessus", 
                        "qualys", "openvas", "nmap", "port scan", "finding", "remediation"]
        vuln_score = sum(1 for kw in vuln_keywords if kw in text_lower)
        if vuln_score >= 3 or "scan" in name_lower or "vuln" in name_lower:
            return "vulnerability_scan"

        # Architecture document indicators
        arch_keywords = ["architecture", "component", "microservice", "api gateway", "load balancer",
                        "database", "deployment", "infrastructure", "topology", "data flow",
                        "system design", "high level design", "hld", "lld", "detailed design"]
        arch_score = sum(1 for kw in arch_keywords if kw in text_lower)
        if arch_score >= 3 or "architect" in name_lower or "design" in name_lower or "hld" in name_lower:
            return "architecture_doc"

        # Policy document indicators
        policy_keywords = ["policy", "compliance", "regulation", "standard", "requirement",
                          "control", "iso 27001", "nist", "soc 2", "gdpr", "hipaa", "pci"]
        policy_score = sum(1 for kw in policy_keywords if kw in text_lower)
        if policy_score >= 3 or "policy" in name_lower or "compliance" in name_lower:
            return "policy"

        # Configuration indicators
        config_keywords = ["server", "port", "host", "config", "setting", "parameter",
                          "environment", "variable", "connection string"]
        config_score = sum(1 for kw in config_keywords if kw in text_lower)
        if config_score >= 3 or "config" in name_lower:
            return "config"

        return "other"
