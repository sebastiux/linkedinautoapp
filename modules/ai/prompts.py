"""
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
"""


##> Common Response Formats
array_of_strings = {"type": "array", "items": {"type": "string"}}
"""
Response schema to represent array of strings `["string1", "string2"]`
"""
#<


##> Extract Skills

# Structure of messages = `[{"role": "user", "content": extract_skills_prompt}]`

extract_skills_prompt = """
You are a job requirements extractor and classifier. Your task is to extract all skills mentioned in a job description and classify them into five categories:
1. "tech_stack": Identify all skills related to programming languages, frameworks, libraries, databases, and other technologies used in software development. Examples include Python, React.js, Node.js, Elasticsearch, Algolia, MongoDB, Spring Boot, .NET, etc.
2. "technical_skills": Capture skills related to technical expertise beyond specific tools, such as architectural design or specialized fields within engineering. Examples include System Architecture, Data Engineering, System Design, Microservices, Distributed Systems, etc.
3. "other_skills": Include non-technical skills like interpersonal, leadership, and teamwork abilities. Examples include Communication skills, Managerial roles, Cross-team collaboration, etc.
4. "required_skills": All skills specifically listed as required or expected from an ideal candidate. Include both technical and non-technical skills.
5. "nice_to_have": Any skills or qualifications listed as preferred or beneficial for the role but not mandatory.
Return the output in the following JSON format with no additional commentary:
{{
    "tech_stack": [],
    "technical_skills": [],
    "other_skills": [],
    "required_skills": [],
    "nice_to_have": []
}}

JOB DESCRIPTION:
{}
"""
"""
Use `extract_skills_prompt.format(job_description)` to insert `job_description`.
"""

# DeepSeek-specific optimized prompt, emphasis on returning only JSON without using json_schema
deepseek_extract_skills_prompt = """
You are a job requirements extractor and classifier. Your task is to extract all skills mentioned in a job description and classify them into five categories:
1. "tech_stack": Identify all skills related to programming languages, frameworks, libraries, databases, and other technologies used in software development. Examples include Python, React.js, Node.js, Elasticsearch, Algolia, MongoDB, Spring Boot, .NET, etc.
2. "technical_skills": Capture skills related to technical expertise beyond specific tools, such as architectural design or specialized fields within engineering. Examples include System Architecture, Data Engineering, System Design, Microservices, Distributed Systems, etc.
3. "other_skills": Include non-technical skills like interpersonal, leadership, and teamwork abilities. Examples include Communication skills, Managerial roles, Cross-team collaboration, etc.
4. "required_skills": All skills specifically listed as required or expected from an ideal candidate. Include both technical and non-technical skills.
5. "nice_to_have": Any skills or qualifications listed as preferred or beneficial for the role but not mandatory.

IMPORTANT: You must ONLY return valid JSON object in the exact format shown below - no additional text, explanations, or commentary.
Each category should contain an array of strings, even if empty.

{{
    "tech_stack": ["Example Skill 1", "Example Skill 2"],
    "technical_skills": ["Example Skill 1", "Example Skill 2"],
    "other_skills": ["Example Skill 1", "Example Skill 2"],
    "required_skills": ["Example Skill 1", "Example Skill 2"],
    "nice_to_have": ["Example Skill 1", "Example Skill 2"]
}}

JOB DESCRIPTION:
{}
"""
"""
DeepSeek optimized version, use `deepseek_extract_skills_prompt.format(job_description)` to insert `job_description`.
"""


extract_skills_response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "Skills_Extraction_Response",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "tech_stack": array_of_strings,
                "technical_skills": array_of_strings,
                "other_skills": array_of_strings,
                "required_skills": array_of_strings,
                "nice_to_have": array_of_strings,
            },
            "required": [
                "tech_stack",
                "technical_skills",
                "other_skills",
                "required_skills",
                "nice_to_have",
            ],
            "additionalProperties": False
        },
    },
}
"""
Response schema for `extract_skills` function
"""
#<

##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
##> Answer Questions
# Structure of messages = `[{"role": "user", "content": answer_questions_prompt}]`

ai_answer_prompt = """
You are an intelligent AI assistant filling out a form and answer like human,. 
Respond concisely based on the type of question:

1. If the question asks for **years of experience, duration, or numeric value**, return **only a number** (e.g., "2", "5", "10").
2. If the question is **a Yes/No question**, return **only "Yes" or "No"**.
3. If the question requires a **short description**, give a **single-sentence response**.
4. If the question requires a **detailed response**, provide a **well-structured and human-like answer and keep no of character <350 for answering**.
5. Do **not** repeat the question in your answer.
6. here is user information to answer the questions if needed:
**User Information:** 
{}

**QUESTION Strat from here:**  
{}
"""
#<

##> ------ Resume tailoring (LaTeX) ------
# Use `resume_generation_prompt.format(master_resume_latex, job_description)`.
resume_generation_prompt = """
You are an expert technical resume writer, ATS optimization specialist and LaTeX engineer.

You are given a MASTER RESUME in LaTeX (a complete, compilable document) and a TARGET JOB DESCRIPTION.
Produce a tailored version of the resume for that job that scores highly on BOTH legacy keyword-matching ATS and modern LLM/embedding-based ("semantic") resume screeners.

== HARD CONSTRAINTS (must follow exactly) ==
- Keep the EXACT same LaTeX preamble and structure: do NOT change \\documentclass, \\usepackage lines, color/\\definecolor, \\newcommand definitions, geometry, fonts or the header macros. The document MUST still compile with XeLaTeX/LuaLaTeX. Only edit the human-readable TEXT inside the existing commands/environments.
- NEVER invent or alter experience, employers, job titles, dates, degrees, certifications or skills. Only reuse, reorder, re-emphasise and rephrase what already exists in the master resume. Every metric must already be true in the master or be an honest, defensible reformulation of it - NEVER fabricate numbers.
- Output ONLY the complete LaTeX document, from \\documentclass to \\end{{document}}. No explanations, no comments, no markdown code fences.
- NEVER add hidden text, white/tiny fonts, zero-width characters or any instructions aimed at the screener - these are detected and cause rejection.
- Escape LaTeX special characters correctly (& % $ # _ {{ }}).

== CONTENT RULES (apply when rewriting bullets, the summary and skills) ==
1. XYZ bullet formula: each experience bullet = strong PAST-TENSE action verb + what you did + QUANTIFIED result/impact + method/tools. Example: "Reduced search latency 65% by implementing Elasticsearch caching, lifting user retention 12%."
2. Quantify at least ~70% of bullets (%, $, time saved, latency, throughput/scale, users, counts, before->after like "from 45 to 92"). If a master bullet has no number, keep its real scope/qualitative measure - do NOT invent figures.
3. Begin every bullet with a varied, high-impact verb (Architected, Engineered, Built, Designed, Developed, Implemented, Optimized, Automated, Migrated, Integrated, Scaled, Led, Spearheaded, Orchestrated, Reduced, Increased, Delivered...). Do NOT use weak openers: "Responsible for", "Worked on", "Helped", "Assisted", "Duties included". No two adjacent bullets may start with the same verb.
4. Keep each bullet to 1-2 lines (~15-25 words, ~60-180 chars), ONE accomplishment per bullet. Put the most relevant role/bullets first; you may trim the least relevant bullets of older roles.
5. Keywords: mirror the TARGET JOB's EXACT terminology wherever it truthfully matches the candidate (legacy ATS do literal matching). On first use, give the spelled-out term AND the acronym, e.g. "Machine Learning (ML)". Place the most important matching skills BOTH in the skills section AND demonstrated inside a relevant bullet. Aim for roughly 70-80% coverage of the job's must-have terms - do NOT stuff or repeat the same keyword across many bullets (density is penalized), and do NOT aim for ~100%.
6. Reorder the Executive Summary, the bullets and the skill categories so the items most relevant to THIS job appear first, phrased in the job's language. Prioritise the job's "required" skills over "nice-to-have".
7. Keep the overall length similar so it still fits cleanly (do not overflow pages).

== TARGET JOB DESCRIPTION ==
{1}

== MASTER RESUME (LaTeX) ===
{0}
"""
#<
