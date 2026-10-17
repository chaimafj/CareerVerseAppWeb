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


def sequence_task(prompt, context, options, order, explanation, skill):
    return {
        "prompt": prompt, "kind": "sequence", "workspace": {"context": context, "order": order},
        "options": options, "correct": list(range(len(options))), "skill": skill,
        "explanation": explanation, "example": "\n".join(
            f"{position}. {options[index]}" for position, index in enumerate(order, 1)
        ),
    }


PREMIUM_LABS = [
    {
        "career": "angular", "title": "Launch-day checkout rescue",
        "scenario": "You are repairing a student subscription portal before release. "
                    "Repair code fragments and arrange a controlled release workflow. "
                    "Inspect the surrounding code and review each step before release. "
                    "Your edits are evaluated after submission; no code is executed.",
        "objectives": ["Repair a server-authoritative payment check", "Cancel stale search requests",
                       "Restore accessible validation", "Surface errors without losing input",
                       "Sequence a guarded release"],
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
            sequence_task(
                "Build the release gate from first step to last. Use every stage once.",
                "The repair is ready for review. Validation must precede staging; staging checks precede production exposure.",
                ["Promote the validated build to production", "Run type checks and authorization regression tests",
                 "Verify checkout and error recovery in staging", "Deploy the validated build to staging"],
                [1, 3, 2, 0],
                "Check the repair, deploy the same validated build to staging, verify realistic flows, then promote it with monitoring.",
                "release quality"),
        ],
    },
    {
        "career": "cloud", "title": "Restore service under pressure",
        "scenario": "Build a resilient registration architecture using five visual design workspaces. "
                    "Place missing components in diagrams, then plan a recovery drill. Place a component from the bank into the "
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
            sequence_task(
                "Arrange the backup recovery drill in operational order.",
                "Use an isolated recovery environment. Validate restored records before moving any traffic.",
                ["Validate restored data and application behavior", "Restore into an isolated recovery environment",
                 "Record verified recovery time and follow-up actions", "Select and verify an independently stored backup"],
                [3, 1, 0, 2],
                "A separate failure domain is essential. Verify a backup, restore it in isolation, test the recovered application and record measured recovery evidence.",
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
            sequence_task(
                "Arrange the recovery verification workflow after the affected sessions have been revoked.",
                "Evidence has already been preserved. Recovery must use a trusted identity channel before issuing a fresh session.",
                ["Verify old-session rejection and new-session owner checks", "Complete trusted identity recovery",
                 "Record verified recovery and monitor for recurrence", "Issue a new session after MFA"],
                [1, 3, 0, 2],
                "Establish trusted identity, issue a fresh MFA-backed session, test old and new access boundaries, then document and monitor recovery.",
                "recovery verification"),
        ],
    },
]
