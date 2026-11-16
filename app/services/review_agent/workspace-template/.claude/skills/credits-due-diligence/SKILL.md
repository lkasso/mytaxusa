---
name: credits-due-diligence
description: Check each dependent and each credit claimed, and write the questions a preparer must ask when information looks inconsistent. Use whenever the return has dependents or claims a credit.
---
A preparer must make reasonable inquiries when the information given looks incorrect, inconsistent, or incomplete, and must record the question and the answer.

For each dependent in return.json, check the qualifying-child tests:
- Relationship, months lived with the taxpayer (more than half the year), age (under 19, or under 24 and a full-time student), own support, joint return.
- A dependent aged 19 or over who is not a student does not qualify as a qualifying child.
- If claim_credit is Yes and no dependent clearly qualifies, the credit claim is suspect.

If a dependent is new this year (not in prior.json), that alone needs a question: what changed, whether the dependent lived with the taxpayer more than half the year, and whether anyone else could claim the dependent.

When something is inconsistent, do not decide the answer. Write a client question:
- question: one plain sentence the taxpayer can answer.
- reason: why a preparer must ask, with the specific facts you saw.

The diagnostics are the source of truth for what this product supports. Do not repeat a diagnostics finding as a separate judgment finding. Add the question, and point to the diagnostics code in the reason.
