import os
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

IGNORE_DIRS = ["venv", "__pycache__", "site-packages"]

pdf = SimpleDocTemplate("project_blueprint.pdf")

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleStyle",
    parent=styles["Heading1"],
    textColor=colors.darkblue,
    fontSize=18,
    spaceAfter=10
)

file_style = ParagraphStyle(
    "FileStyle",
    parent=styles["Heading2"],
    textColor=colors.darkgreen,
    fontSize=14,
    spaceAfter=6
)

route_style = ParagraphStyle(
    "RouteStyle",
    parent=styles["Normal"],
    textColor=colors.red,
    fontSize=10
)

import_style = ParagraphStyle(
    "ImportStyle",
    parent=styles["Normal"],
    textColor=colors.purple,
    fontSize=10
)

content = []

content.append(Paragraph("PROJECT BLUEPRINT REPORT", title_style))
content.append(Spacer(1, 10))

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)

            content.append(Paragraph(f"FILE: {path}", file_style))

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()

                    routes = re.findall(r"@app\.route\(['\"].*?['\"]", data)
                    imports = re.findall(r"^(import .*|from .* import .*)", data, re.M)

                    if routes:
                        content.append(Paragraph("ROUTES:", route_style))
                        for r in routes:
                            content.append(Paragraph(r, route_style))

                    if imports:
                        content.append(Paragraph("IMPORTS:", import_style))
                        for i in imports[:10]:
                            content.append(Paragraph(i, import_style))

                    content.append(Spacer(1, 10))

            except:
                pass

pdf.build(content)

print("✅ PDF created: project_blueprint.pdf")
