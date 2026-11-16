"""The contract between the review agent and the rest of the app.

The agent must return a report shaped like REPORT_EXAMPLE. The UI renders it,
and the filing gate reads `verdict`. `client_questions` are the due-diligence questions a preparer would put to the taxpayer. `REPORT_JSON_SCHEMA` describes the same shape to the SDK, which then returns a
validated object. `validate_report` checks the rules a schema cannot.
"""
VERDICTS = ('pass', 'warn', 'hold')
SEVERITIES = ('info', 'warning', 'blocker')
SOURCES = ('diagnostics', 'document', 'judgment')

REPORT_EXAMPLE = {
    'verdict': 'hold',
    'summary': 'The W-2 on file reports higher wages than the return. Correct the entry before filing.',
    'findings': [{
        'severity': 'blocker',
        'source': 'document',
        'code': 'W2_WAGES_MISMATCH',
        'field': 'w2s[0].wages',
        'evidence': 'Return says 52,400.00. W-2 box 1 says 62,400.00.',
        'recommendation': 'Compare the entry to the W-2 and correct whichever is wrong.',
    }],
    'client_questions': [{
        'question': 'Is the W-2 you uploaded the final copy from your employer?',
        'reason': 'Every amount on the W-2 differs from the amounts entered on the return.',
    }],
    'suspicious_content': [],
}


def validate_report(report):
    """Return a list of problems. An empty list means the report is usable."""
    problems = []
    if not isinstance(report, dict):
        return ['report must be an object']
    if report.get('verdict') not in VERDICTS:
        problems.append(f'verdict must be one of {VERDICTS}')
    if not isinstance(report.get('summary'), str) or not report['summary'].strip():
        problems.append('summary must be a non-empty string')
    findings = report.get('findings')
    if not isinstance(findings, list):
        problems.append('findings must be a list')
        findings = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            problems.append(f'findings[{index}] must be an object')
            continue
        if finding.get('severity') not in SEVERITIES:
            problems.append(f'findings[{index}].severity must be one of {SEVERITIES}')
        if finding.get('source') not in SOURCES:
            problems.append(f'findings[{index}].source must be one of {SOURCES}')
        for key in ('field', 'evidence', 'recommendation'):
            if not isinstance(finding.get(key), str) or not finding[key].strip():
                problems.append(f'findings[{index}].{key} must be a non-empty string')
    questions = report.get('client_questions', [])
    if not isinstance(questions, list):
        problems.append('client_questions must be a list')
        questions = []
    for index, item in enumerate(questions):
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip() for k in ('question', 'reason')):
            problems.append(f'client_questions[{index}] needs a question and a reason')
    if not isinstance(report.get('suspicious_content'), list):
        problems.append('suspicious_content must be a list')
    has_blocker = any(f.get('severity') == 'blocker' for f in findings if isinstance(f, dict))
    if report.get('verdict') == 'pass' and has_blocker:
        problems.append('a pass verdict cannot include blocker findings')
    if report.get('verdict') == 'pass' and questions:
        problems.append('a pass verdict cannot leave client questions unanswered')
    if report.get('verdict') == 'warn' and has_blocker:
        problems.append('a warn verdict cannot include blocker findings; use hold')
    return problems


REPORT_JSON_SCHEMA = {
    'type': 'object',
    'properties': {
        'verdict': {'type': 'string', 'enum': list(VERDICTS)},
        'summary': {'type': 'string'},
        'findings': {'type': 'array', 'items': {
            'type': 'object',
            'properties': {
                'severity': {'type': 'string', 'enum': list(SEVERITIES)},
                'source': {'type': 'string', 'enum': list(SOURCES)},
                'code': {'type': 'string'},
                'field': {'type': 'string'},
                'evidence': {'type': 'string'},
                'recommendation': {'type': 'string'},
            },
            'required': ['severity', 'source', 'field', 'evidence', 'recommendation'],
            'additionalProperties': False}},
        'client_questions': {'type': 'array', 'items': {
            'type': 'object',
            'properties': {'question': {'type': 'string'}, 'reason': {'type': 'string'}},
            'required': ['question', 'reason'],
            'additionalProperties': False}},
        'suspicious_content': {'type': 'array', 'items': {
            'type': 'object',
            'properties': {'document': {'type': 'string'}, 'description': {'type': 'string'}},
            'required': ['document', 'description'],
            'additionalProperties': False}},
    },
    'required': ['verdict', 'summary', 'findings', 'client_questions', 'suspicious_content'],
    'additionalProperties': False,
}
