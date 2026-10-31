# LABELING — hand-label rule for the prompt experiment

Written by Meena on 2026-10-31, before seeing any model verdicts.

I label a posting RELEVANT for the persona if:
1. Target Role: It aligns with entry-level / early-career AI Engineer, Data Scientist, Data Engineer, or BI Analyst tracks.
2. Full-Time Early Career: It is a full-time position (no internships, co-ops, or temp roles) and asks for 0–2 years of experience (strictly rejecting senior, staff, principal, or managerial titles).
3. Location & Work Authorization: It is located in the US / Remote and does not explicitly disqualify candidates requiring H-1B visa sponsorship.
4. Core Tech Match: At least two primary technical skills listed in the persona (e.g., Python, SQL, PyTorch/TensorFlow, or PowerBI/Tableau) appear in the job requirements excerpt.

Otherwise, I label it NOT RELEVANT. When unsure (e.g., vague sponsorship terms or ambiguous level requirements), I label NOT RELEVANT and write "unsure: <reason>" in the notes column.