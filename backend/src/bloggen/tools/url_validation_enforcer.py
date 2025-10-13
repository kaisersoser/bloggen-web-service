"""
URL Validation Enforcer - Forces fact checker to validate URLs before content approval.

This tool creates a validation loop that ensures the fact checker cannot approve
content without first validating all URLs and providing evidence of validation.
"""

import logging
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .url_validation_tool import URLValidationTool, BulkURLValidationTool


@dataclass
class ValidationLoopResult:
    """Result of validation loop enforcement"""

    validation_required: bool
    urls_found: List[str]
    validation_evidence_required: str
    enforcement_instructions: str
    retry_needed: bool = False
    compliance_score: float = 0.0


class URLValidationEnforcer:
    """
    Enforces URL validation compliance in fact checking phase.

    This tool creates a validation loop that:
    1. Extracts URLs from content before fact checking
    2. Generates mandatory validation requirements
    3. Checks fact checker output for validation evidence
    4. Forces retry if validation requirements not met
    5. Provides compliance scoring and feedback
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.url_validator = URLValidationTool()
        self.bulk_validator = BulkURLValidationTool()

        # Validation evidence patterns to look for in fact checker output
        self.validation_evidence_patterns = [
            r"URL.*(?:validated|checked|verified|tested)",
            r"(?:validated|checked|verified|tested).*URL",
            r"link.*(?:validation|verification|check)",
            r"(?:validation|verification|check).*link",
            r"accessibility.*(?:confirmed|verified|tested)",
            r"URLValidationTool.*(?:used|executed|run)",
            r"BulkURLValidationTool.*(?:used|executed|run)",
            r"status.*(?:200|working|accessible)",
            r"broken.*(?:link|URL).*(?:found|detected|identified)",
            r"working.*(?:link|URL).*(?:confirmed|verified)",
        ]

    def extract_urls_from_content(self, content: str) -> List[str]:
        """Extract all URLs from content using multiple patterns"""
        url_patterns = [
            r'https?://[^\s\)\]\}\'"]+',  # Plain URLs
            r"\[([^\]]+)\]\(([^)]+)\)",  # Markdown links [text](url)
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>',  # HTML links
        ]

        urls = []
        for pattern in url_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) > 1:
                    # Extract URL from capture group (markdown/HTML)
                    url = (
                        match.group(2)
                        if "href=" not in match.group(0)
                        else match.group(1)
                    )
                else:
                    # Plain URL
                    url = match.group(0)

                # Clean and validate URL format
                url = url.strip(".,;!?)\"'")
                if url and url.startswith(("http://", "https://")):
                    urls.append(url)

        return list(set(urls))  # Remove duplicates

    def generate_validation_requirements(
        self, urls: List[str], topic: str
    ) -> ValidationLoopResult:
        """Generate mandatory validation requirements for fact checker"""
        if not urls:
            return ValidationLoopResult(
                validation_required=False,
                urls_found=[],
                validation_evidence_required="No URLs found - no validation required.",
                enforcement_instructions="No URL validation needed for this content.",
            )

        # Create detailed validation requirements
        validation_evidence = self._create_validation_evidence_template(urls)
        enforcement_instructions = self._create_enforcement_instructions(urls, topic)

        return ValidationLoopResult(
            validation_required=True,
            urls_found=urls,
            validation_evidence_required=validation_evidence,
            enforcement_instructions=enforcement_instructions,
        )

    def _create_validation_evidence_template(self, urls: List[str]) -> str:
        """Create template for required validation evidence"""
        template_lines = [
            "🔍 MANDATORY URL VALIDATION EVIDENCE REQUIRED:",
            "=" * 50,
            "",
            "You MUST validate each URL below and provide evidence:",
            "",
        ]

        for i, url in enumerate(urls, 1):
            template_lines.extend(
                [
                    f"{i}. URL: {url}",
                    f"   ✅ VALIDATION REQUIRED: Use URLValidationTool to test accessibility",
                    f"   📋 EVIDENCE REQUIRED: Report status code, accessibility, and any errors",
                    f"   🔧 ACTION REQUIRED: Replace if broken, confirm if working",
                    "",
                ]
            )

        template_lines.extend(
            [
                "VALIDATION COMPLETION CHECKLIST:",
                "□ All URLs tested with URLValidationTool",
                "□ Status codes reported for each URL",
                "□ Broken URLs identified and flagged for replacement",
                "□ Working URLs confirmed as accessible",
                "□ Validation summary provided with evidence",
                "",
                "⚠️ CRITICAL: Content cannot be approved without completing ALL validations above.",
            ]
        )

        return "\n".join(template_lines)

    def _create_enforcement_instructions(self, urls: List[str], topic: str) -> str:
        """Create detailed enforcement instructions for fact checker"""
        instructions = f"""
🚨 MANDATORY URL VALIDATION PROTOCOL - FACT CHECKER ENFORCEMENT

TOPIC: {topic}
URLs REQUIRING VALIDATION: {len(urls)}

STEP-BY-STEP VALIDATION REQUIREMENTS:

1. 🔍 URL DISCOVERY PHASE:
   - Extract and identify all {len(urls)} URLs in the content
   - List each URL that requires validation
   - Confirm no URLs were missed

2. 🛠️ VALIDATION EXECUTION PHASE:
   - Use URLValidationTool for each individual URL
   - OR use BulkURLValidationTool for batch validation
   - Record exact results: status codes, errors, response times
   - Document accessibility status for each URL

3. 📋 EVIDENCE DOCUMENTATION PHASE:
   - Report validation results in your fact-check output
   - Include specific status codes and error messages
   - Clearly mark working vs broken URLs
   - Provide replacement suggestions for broken URLs

4. 🔧 CORRECTIVE ACTION PHASE:
   - Flag any broken URLs for immediate replacement
   - Suggest working alternatives where possible
   - Recommend removal if no alternatives exist
   - Confirm all working URLs are properly formatted

5. ✅ COMPLIANCE VERIFICATION PHASE:
   - Verify all {len(urls)} URLs have been validated
   - Confirm evidence is documented in your output
   - Ensure no broken URLs remain in final content
   - Provide validation summary with compliance confirmation

⚠️ ENFORCEMENT RULES:
- Content CANNOT be approved without completing ALL validation steps
- Missing validation evidence will result in automatic retry
- Broken URLs must be flagged and addressed
- Validation results must be explicitly documented
- Tool usage evidence must be visible in output

🎯 SUCCESS CRITERIA:
- All {len(urls)} URLs validated and documented
- Clear evidence of URLValidationTool usage
- Broken URLs identified and flagged
- Validation summary provided with results
- Compliance checklist completed

FAILURE TO COMPLY WILL TRIGGER AUTOMATIC RETRY WITH ENHANCED REQUIREMENTS.
"""
        return instructions

    def check_validation_compliance(
        self, fact_checker_output: str, expected_urls: List[str]
    ) -> Tuple[bool, float, List[str]]:
        """Check if fact checker output shows evidence of URL validation compliance"""
        if not expected_urls:
            return True, 1.0, ["No URLs to validate - compliant"]

        compliance_issues = []
        evidence_score = 0.0
        max_possible_score = (
            len(expected_urls) * 4
        )  # 4 points per URL (tool usage, status, results, action)

        # Check for tool usage evidence
        tool_usage_found = any(
            re.search(pattern, fact_checker_output, re.IGNORECASE)
            for pattern in [
                "URLValidationTool",
                "BulkURLValidationTool",
                "url.*validation",
                "link.*check",
            ]
        )

        if tool_usage_found:
            evidence_score += len(expected_urls)  # 1 point per URL for tool usage
        else:
            compliance_issues.append("❌ No evidence of URLValidationTool usage found")

        # Check for validation evidence patterns
        evidence_patterns_found = sum(
            1
            for pattern in self.validation_evidence_patterns
            if re.search(pattern, fact_checker_output, re.IGNORECASE)
        )

        evidence_score += min(
            evidence_patterns_found, len(expected_urls)
        )  # Max 1 point per URL

        # Check for specific URL mentions and validation results
        urls_mentioned = 0
        status_codes_found = 0

        for url in expected_urls:
            # Check if URL is mentioned in output
            if url in fact_checker_output:
                urls_mentioned += 1
                evidence_score += 1  # 1 point per URL mentioned

            # Check for status code patterns near this URL
            url_context = self._get_url_context(
                fact_checker_output, url, context_chars=200
            )
            if re.search(
                r"\b(?:200|404|403|500|timeout|error|working|broken|accessible)\b",
                url_context,
                re.IGNORECASE,
            ):
                status_codes_found += 1
                evidence_score += 1  # 1 point per URL with status info

        if urls_mentioned < len(expected_urls):
            compliance_issues.append(
                f"❌ Only {urls_mentioned}/{len(expected_urls)} URLs mentioned in validation output"
            )

        if status_codes_found < len(expected_urls):
            compliance_issues.append(
                f"❌ Only {status_codes_found}/{len(expected_urls)} URLs have status/result information"
            )

        # Check for validation summary
        has_summary = any(
            keyword in fact_checker_output.lower()
            for keyword in [
                "validation summary",
                "url validation",
                "link check",
                "validation complete",
            ]
        )

        if has_summary:
            evidence_score += 2  # Bonus points for summary
        else:
            compliance_issues.append("❌ No validation summary found in output")

        # Calculate compliance score
        compliance_score = (
            evidence_score / max_possible_score if max_possible_score > 0 else 1.0
        )
        is_compliant = compliance_score >= 0.7  # Require 70% compliance

        if not is_compliant:
            compliance_issues.append(
                f"❌ Compliance score too low: {compliance_score:.1%} (minimum 70% required)"
            )

        return is_compliant, compliance_score, compliance_issues

    def _get_url_context(self, text: str, url: str, context_chars: int = 200) -> str:
        """Get text context around a specific URL"""
        url_pos = text.find(url)
        if url_pos == -1:
            return ""

        start = max(0, url_pos - context_chars)
        end = min(len(text), url_pos + len(url) + context_chars)
        return text[start:end]

    def create_retry_requirements(
        self, compliance_issues: List[str], urls: List[str]
    ) -> str:
        """Create enhanced requirements for retry attempt"""
        retry_instructions = f"""
🚨 URL VALIDATION COMPLIANCE FAILURE - RETRY REQUIRED

COMPLIANCE ISSUES IDENTIFIED:
{chr(10).join(compliance_issues)}

ENHANCED VALIDATION REQUIREMENTS FOR RETRY:

🔍 MANDATORY VALIDATION CHECKLIST:
"""

        for i, url in enumerate(urls, 1):
            retry_instructions += f"""
{i}. URL: {url}
   🛠️ REQUIRED ACTION: Run URLValidationTool("{url}")
   📋 REQUIRED OUTPUT: Report exact status code and accessibility
   ✅ REQUIRED EVIDENCE: Show tool execution results
   🔧 REQUIRED FOLLOW-UP: State specific action (keep/replace/remove)
"""

        retry_instructions += """
⚠️ COMPLIANCE ENFORCEMENT:
- You MUST use URLValidationTool for each URL above
- You MUST report the exact results in your output
- You MUST show evidence of tool usage
- You MUST provide validation summary
- Content approval is BLOCKED until compliance achieved

📝 REQUIRED OUTPUT FORMAT:
"🔍 URL VALIDATION RESULTS:
1. Tested [URL] with URLValidationTool: [STATUS] - [ACTION]
2. Tested [URL] with URLValidationTool: [STATUS] - [ACTION]
...
✅ VALIDATION SUMMARY: [X] URLs validated, [Y] working, [Z] broken"

THIS IS A COMPLIANCE RETRY - FOLLOW ALL REQUIREMENTS EXACTLY.
"""

        return retry_instructions

    def enforce_validation_loop(self, content: str, topic: str) -> ValidationLoopResult:
        """Main enforcement method - creates validation requirements for content"""
        self.logger.info(f"🔒 Starting URL Validation Enforcement for topic: {topic}")

        # Extract URLs from content
        urls = self.extract_urls_from_content(content)
        self.logger.info(f"📊 Found {len(urls)} URLs requiring validation enforcement")

        if not urls:
            self.logger.info("✅ No URLs found - no validation enforcement needed")
            return ValidationLoopResult(
                validation_required=False,
                urls_found=[],
                validation_evidence_required="No URLs found - no validation required.",
                enforcement_instructions="No URL validation enforcement needed.",
            )

        # Generate validation requirements
        result = self.generate_validation_requirements(urls, topic)
        self.logger.info(f"🔒 Generated validation requirements for {len(urls)} URLs")

        return result


def create_validation_enforcer() -> URLValidationEnforcer:
    """Factory function to create URLValidationEnforcer instance"""
    return URLValidationEnforcer()
