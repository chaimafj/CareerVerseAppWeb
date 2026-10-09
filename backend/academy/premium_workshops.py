"""Original educational workspaces. Code repairs are checked, never executed."""


def code_task(prompt, before, after, answer, explanation, skill):
    return {
        "prompt": prompt, "kind": "code", "workspace": {"before": before, "after": after},
        "options": [answer, "__invalid_repair__"], "correct": [0],
        "skill": skill, "explanation": explanation,
        "example": before + answer + after,
    }


def architecture_task(prompt, nodes, gap, options, correct, explanation, skill):
    return {
        "prompt": prompt, "kind": "architecture",
        "workspace": {"nodes": nodes, "gap": gap},
        "options": options, "correct": [correct], "skill": skill,
        "explanation": explanation,
        "example": " -> ".join(options[correct] if index == gap else node for index, node in enumerate(nodes)),
    }


def evidence_task(prompt, context, options, correct, explanation, skill):
    return {
        "prompt": prompt, "kind": "evidence", "workspace": {"context": context},
        "options": options, "correct": correct, "skill": skill, "explanation": explanation,
        "example": "\n".join(options[index] for index in correct),
    }


PREMIUM_LABS = [
    {
        "career": "angular", "title": "Launch-day checkout rescue",
        "scenario": "You are repairing a student subscription portal before release. "
                    "Complete five missing code fragments in an Angular review workspace. "
                    "Inspect the surrounding code and enter the exact replacement requested. "
                    "Your edits are evaluated after submission; no code is executed.",
        "objectives": ["Repair a server-authoritative payment check", "Cancel stale search requests",
                       "Restore accessible validation", "Surface errors without losing input",
                       "Add an authorization regression assertion"],
        "questions": [
            code_task(
                "Repair the condition: access must depend on the API's is_premium field. Enter the property expression.",
                "const status = await api.billingStatus();\nif (", ") {\n  showPremiumContent();\n} else {\n  showPending();\n}",
                "status.is_premium",
                "The signed payment webhook updates server entitlement. Query parameters and local storage cannot grant access.",
                "payment boundaries"),
            code_task(
                "Replace the missing RxJS operator with its name so a newer search cancels the previous request.",
                "terms.pipe(\n  debounceTime(250),\n  distinctUntilChanged(),\n  ",
                "(term => api.search(term))\n).subscribe(renderResults);",
                "switchMap",
                "switchMap unsubscribes from the previous search observable. mergeMap permits out-of-order results; debounce alone does not solve stale responses.",
                "reactive state"),
            code_task(
                "Link the input to its error text. Enter the exact accessibility attribute name.",
                '<label for="email">Email</label>\n<input id="email" ', '="email-error">\n<p id="email-error">Enter a valid email</p>',
                "aria-describedby",
                "aria-describedby associates descriptive error text with the field. A label identifies the field, while this attribute explains its error.",
                "accessibility"),
            code_task(
                "The save fails. Complete the function name to notify the user without clearing their form.",
                "try {\n  await api.save(form.value);\n} catch (error) {\n  ", "(error);\n  // Keep the existing form values for retry.\n}",
                "showError",
                "Explicit error feedback is necessary. Calling showSuccess would hide the failure; clearing input would prevent an easy retry.",
                "reliability"),
            code_task(
                "Complete the expected HTTP status for a student requesting another student's private result. Enter the number.",
                "const response = await studentClient.get(otherStudentResultUrl);\nexpect(response.status).toBe(", ");",
                "404",
                "This API filters private results by owner, so another student's result is not found (404). This avoids confirming that a private record exists.",
                "release quality"),
        ],
    },
    {
        "career": "cloud", "title": "Restore service under pressure",
        "scenario": "Build a resilient registration architecture using five visual design workspaces. "
                    "Each diagram has one missing component. Place a component from the bank into the "
                    "highlighted slot, review the resulting data flow, and justify the design through the final feedback. "
                    "The diagrams are simplified educational models, not deployed infrastructure.",
        "objectives": ["Distribute incoming traffic", "Absorb demand spikes",
                       "Bound database access", "Handle duplicate operations", "Separate backup failure domains"],
        "questions": [
            architecture_task(
                "Two API instances should share traffic and unhealthy instances must be bypassed. Fill the highlighted slot.",
                ["Student clients", "", "Healthy API pool", "Private database"], 1,
                ["Single public database", "Load balancer", "Email server", "Local browser cache"], 1,
                "A load balancer routes requests to healthy instances. It does not replace database protection or make an unhealthy application correct.",
                "traffic distribution"),
            architecture_task(
                "Registration processing is asynchronous. Place a durable buffer between the API and bounded workers.",
                ["Registration API", "", "Bounded worker pool", "Registration database"], 1,
                ["Unbounded recursive retries", "Static file server", "Durable queue", "Client cookie"], 2,
                "A durable queue absorbs bursts and supports controlled consumption. Workers still need idempotency and backpressure; a queue is not infinite capacity.",
                "backpressure"),
            architecture_task(
                "The database allows 100 connections. Insert the component that reuses and limits application connections.",
                ["API + workers", "", "Private database"], 1,
                ["Bounded connection pool", "Unlimited worker replicas", "Public admin console", "Per-request connection storm"], 0,
                "A bounded pool reuses connections and prevents uncontrolled growth. Sum the pools across all replicas against the database connection budget.",
                "capacity planning"),
            architecture_task(
                "A client retries a timed-out paid registration. Place a server-side safeguard before creating a new registration.",
                ["Request with operation ID", "", "Atomic registration write", "Recorded response"], 1,
                ["Random new charge ID", "Browser success flag", "Disable transaction", "Idempotency lookup"], 3,
                "The operation ID is checked against persisted outcomes. A transaction or uniqueness rule must also guard concurrent duplicate requests.",
                "distributed reliability"),
            architecture_task(
                "A host failure must not destroy both production data and backups. Choose the final destination for encrypted backups.",
                ["Production database", "Encrypted backup job", ""], 2,
                ["Same host temporary folder", "Isolated backup storage", "Public bucket without access control", "Browser localStorage"], 1,
                "Use a separate failure domain with restricted access, retention and restore drills. Encryption alone does not prove that restoration works.",
                "disaster recovery"),
        ],
    },
    {
        "career": "cybersecurity", "title": "Investigate a suspicious account",
        "scenario": "Work through a fictional defensive incident dossier. Select relevant log rows, "
                    "identify an authorization defect in code, and review a containment diagram. "
                    "The evidence uses synthetic users and documentation-only network addresses. "
                    "Distinguish suspicious evidence from proof and preserve privacy.",
        "objectives": ["Correlate session and device changes", "Separate suspicious from normal events",
                       "Repair an owner-filter defect", "Choose safe containment", "Verify recovery evidence"],
        "questions": [
            evidence_task(
                "Flag the two events that warrant investigation of session S7. A device change alone is not proof of compromise.",
                "Baseline: student-17 normally uses device D1. Session S7 was issued after MFA at 09:00.",
                ["09:00 MFA success | student-17 | D1 | S7",
                 "09:01 GET /own-profile | D1 | S7 | 200",
                 "09:04 Session S7 reused | new device D9 | 203.0.113.42",
                 "09:05 GET /admin/export | D9 | S7 | 403"], [2, 3],
                "New-device session reuse combined with a denied privileged export warrants investigation. A normal own-profile read and initial MFA success are baseline events, not evidence of an attack.",
                "evidence assessment"),
            evidence_task(
                "Select the two log findings that directly indicate authorization or secret-handling defects.",
                "Audit the following API and logging observations. Only verified defects should enter the remediation list.",
                ["GET /results/42 | owner=student-18 | requester=student-17 | 200",
                 "GET /own-profile | requester=student-17 | 200",
                 "DEBUG support trace | raw_session_token=[synthetic example]",
                 "GET /admin/export | student-role | 403"], [0, 2],
                "A private result returned to a different owner is an authorization defect. Logging raw session credentials is unsafe. Own-profile access and rejected admin access are expected.",
                "access control"),
            code_task(
                "Complete the Django owner filter using the authenticated principal's expression.",
                "result = get_object_or_404(\n    Result.objects.filter(attempt__user=", "),\n    pk=result_id,\n)",
                "request.user",
                "Filter by the server-authenticated request.user, never by an owner ID supplied by the client. This prevents cross-account result access.",
                "secure code review"),
            architecture_task(
                "After session compromise is verified, insert the containment action before secure recovery.",
                ["Verified compromise", "", "Trusted identity recovery", "Fresh MFA login"], 1,
                ["Publish student's details", "Delete all evidence", "Revoke affected sessions", "Share session token"], 2,
                "Revoke affected sessions, preserve evidence and use trusted identity recovery. Publishing identity or deleting logs worsens incident handling.",
                "containment"),
            evidence_task(
                "Select the two verification events that support recovery. Do not assume a success message proves containment.",
                "After revoking S7 and completing trusted recovery, verify access controls.",
                ["09:30 Old session S7 | GET /own-profile | 401",
                 "09:31 Support message | 'probably fixed' | no checks",
                 "09:32 New MFA session S8 | GET /own-profile | 200",
                 "09:33 Old session S7 | GET /private-results | 200"], [0, 2],
                "Rejecting the old session and allowing a verified new MFA session support recovery. Old-session private access means containment failed and requires further action.",
                "recovery verification"),
        ],
    },
]
