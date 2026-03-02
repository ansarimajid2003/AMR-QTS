import markdown
import os

md_file = "AMR-QTS_System_Plan_v3.md"
html_file = "AMR-QTS_System_Plan_v3.html"

with open(md_file, "r", encoding="utf-8") as f:
    text = f.read()

# Convert markdown to html with standard extensions
html_body = markdown.markdown(text, extensions=['fenced_code', 'tables', 'toc'])

# Simple beautiful styling for the PDF
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AMR-QTS System Plan</title>
    <style>
        body {{
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        code {{
            background-color: #f8f9fa;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: Consolas, monospace;
        }}
        pre {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .page-break {{
            page-break-before: always;
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Successfully converted {md_file} to {html_file}")
