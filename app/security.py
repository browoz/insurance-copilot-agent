from __future__ import annotations

import re
from dataclasses import dataclass, field


PUBLIC_DATA_POLICY = (
    "This system uses public CMS Marketplace Public Use Files and local sample data only. "
    "It must not ingest private brokerage files, client documents, credentials, policy numbers, "
    "claims files, driver records, emails, or non-public insurer materials."
)

ADVICE_DISCLAIMER = (
    "This is educational support for comparing public plan data. It is not medical, legal, "
    "financial, tax, or insurance advice. Verify plan details with official CMS or insurer sources."
)


@dataclass(frozen=True)
class SecurityFinding:
    category: str
    detail: str


@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    findings: list[SecurityFinding] = field(default_factory=list)

    @property
    def reason(self) -> str:
        if not self.findings:
            return "allowed"
        return "; ".join(f"{item.category}: {item.detail}" for item in self.findings)


class SecurityGuard:
    """Small deterministic guardrail layer for demoable safety behavior."""

    private_data_patterns = [
        ("private_brokerage_data", re.compile(r"\b(all_risk_insurance_docs|brokerage files?|client files?)\b", re.I)),
        ("credentials", re.compile(r"\b(password|api key|secret|token|credential|login)\b", re.I)),
        ("client_identifiers", re.compile(r"\b(policy number|claim number|driver'?s? licence|driver'?s? license|sin|ssn|date of birth)\b", re.I)),
        ("private_documents", re.compile(r"\b(upload|read|summari[sz]e|ingest)\b.*\b(email|msg|policy document|claim file|autoplus|mvr|client document)\b", re.I)),
    ]

    prompt_injection_patterns = [
        ("prompt_injection", re.compile(r"\b(ignore|bypass|override|forget)\b.*\b(instructions?|policy|guardrails?|system prompt)\b", re.I)),
        ("prompt_extraction", re.compile(r"\b(show|print|reveal|dump)\b.*\b(system prompt|developer message|hidden instructions?|hidden prompt|api key)\b", re.I)),
    ]

    prohibited_advice_patterns = [
        ("regulated_advice", re.compile(r"\b(should i buy|guarantee|best plan for my medical condition|diagnose|treat|legal advice|tax advice)\b", re.I)),
    ]

    def analyze(self, text: str) -> SecurityDecision:
        findings: list[SecurityFinding] = []
        for category, pattern in self.private_data_patterns + self.prompt_injection_patterns:
            if pattern.search(text):
                findings.append(SecurityFinding(category, "Request conflicts with public-data-only or instruction-safety policy."))
        for category, pattern in self.prohibited_advice_patterns:
            if pattern.search(text):
                findings.append(SecurityFinding(category, "Request asks for regulated personalized advice instead of education."))
        return SecurityDecision(allowed=not findings, findings=findings)

    def refusal(self, decision: SecurityDecision) -> str:
        return (
            "I cannot complete that request because it violates the project safety policy. "
            f"Reason: {decision.reason}. "
            f"{PUBLIC_DATA_POLICY} {ADVICE_DISCLAIMER}"
        )

    def attach_disclaimer(self, answer: str) -> str:
        if ADVICE_DISCLAIMER in answer:
            return answer
        return f"{answer}\n\nSafety note: {ADVICE_DISCLAIMER}"
