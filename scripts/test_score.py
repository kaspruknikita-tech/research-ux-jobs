import os
from dotenv import load_dotenv
load_dotenv()

from scoring import score_vacancy

# Вакансия с хорошим описанием — ожидаем enrich=False
vacancy_full = {
    "id": 1,
    "source": "remotive",
    "title": "Senior UX Researcher",
    "company": "Figma",
    "location": "Remote, worldwide",
    "work_format": "remote",
    "description": """
<h2>About the role</h2>
<p>We are looking for a Senior UX Researcher to join our team.</p>
<h2>Responsibilities</h2>
<ul>
  <li>Run mixed methods research (surveys, interviews, usability tests)</li>
  <li>Use Dovetail for synthesis and research ops</li>
  <li>Partner with product and design teams</li>
</ul>
<h2>Requirements</h2>
<ul>
  <li>5+ years of UX research experience</li>
  <li>Experience with Maze, dscout, or similar tools</li>
</ul>
<h2>Benefits</h2>
<ul>
  <li>Fully remote, open to candidates worldwide</li>
  <li>Visa sponsorship and relocation support available</li>
  <li>Salary: $90,000–$130,000/year</li>
</ul>
""",
}

# Вакансия с куцым описанием — ожидаем enrich=True
vacancy_sparse = {
    "id": 2,
    "source": "arbeitnow",
    "title": "UX Researcher",
    "company": "TechCorp",
    "description": "We need a researcher. Apply now.",
}

print("=== Полная вакансия (enrich должен быть False) ===")
r1 = score_vacancy(vacancy_full)
print(f"tier={r1.tier} score={r1.score} enrich={r1.enrichment_used} regex={r1.regex_completeness_score}")
print(f"reason: {r1.reason}")
print()

print("=== Куцая вакансия (enrich должен быть True) ===")
r2 = score_vacancy(vacancy_sparse)
print(f"tier={r2.tier} score={r2.score} enrich={r2.enrichment_used} regex={r2.regex_completeness_score}")
print(f"post_enrichment: {r2.post_enrichment}")
print(f"reason: {r2.reason}")
