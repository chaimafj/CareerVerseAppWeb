"""Applied Premium missions for the extended catalogue; no submitted code is executed."""

from .premium_workshops import architecture_task, code_task, evidence_task, sequence_task


PREMIUM_LABS = [
    {
        "career": "devops", "title": "Release control room",
        "scenario": "A student portal release must pass a delivery gate and a safe canary rollout. "
                    "Build the pipeline, repair a deployment limit, place the traffic-control component "
                    "and inspect synthetic release telemetry before ordering recovery. This is a simulated "
                    "operations workspace; no infrastructure is provisioned.",
        "objectives": ["Sequence a build-once pipeline", "Bound unavailable replicas", "Place a canary router",
                       "Identify release-blocking signals", "Plan compatible recovery"],
        "questions": [
            sequence_task(
                "Assemble the delivery pipeline. Publish only after checks pass; deploy the published digest.",
                "The source change is already reviewed. Use each stage once.",
                ["Deploy the published digest to staging", "Run tests and static checks",
                 "Publish the validated image digest", "Build the immutable image"],
                [1, 3, 2, 0],
                "Run checks before building. Publish the validated immutable artifact and deploy that digest so staging and production use identical software.",
                "delivery pipeline"),
            code_task(
                "The service needs all three replicas available during rollout and permits one surge replica. Enter the maxUnavailable number.",
                "replicas: 3\nstrategy:\n  rollingUpdate:\n    maxSurge: 1\n    maxUnavailable: ", "\n",
                "0", "maxUnavailable: 0 avoids deliberately reducing available replicas during a rolling update. "
                     "Readiness probes and sufficient surge capacity are still necessary.", "rollout configuration"),
            architecture_task(
                "Route a small share of production requests to the canary without changing every client.",
                ["Clients", "", "Stable + canary services", "Request metrics"], 1,
                ["Public database", "Weighted traffic router", "Unbounded retry loop", "Local build cache"], 1,
                "A weighted router controls exposure. Observe comparable stable and canary signals before increasing traffic.",
                "canary traffic"),
            evidence_task(
                "Mark the two signals that block promotion under the stated policy.",
                "Synthetic policy: canary error rate must stay below 1%; readiness must be healthy before promotion.",
                ["Stable: error rate 0.2%, readiness healthy", "Canary: error rate 4.8%",
                 "Canary: readiness failures on 2 of 3 pods", "Build artifact digest matches staging"],
                [1, 2], "The canary exceeds the error threshold and fails readiness. A matching artifact does not excuse user-visible failure.",
                "release telemetry"),
            sequence_task(
                "Order a compatible rollback after a canary failure. The prior build supports the current schema.",
                "Halt exposure before changing workloads; verify recovery before closing the release incident.",
                ["Verify request success and readiness", "Stop promotion and route traffic away from canary",
                 "Record the incident and preserve diagnostics", "Restore the known-good deployment"],
                [1, 3, 0, 2],
                "Contain exposure, restore a schema-compatible deployment, verify user-facing indicators and preserve diagnostics for follow-up.",
                "release recovery"),
        ],
    },
    {
        "career": "machine-learning", "title": "Model promotion investigation",
        "scenario": "A rare-event classifier is proposed for production. Repair its preprocessing pipeline, "
                    "place the inference transform, investigate validation evidence and sequence a guarded "
                    "model promotion. All datasets and metrics are synthetic; no training job runs.",
        "objectives": ["Prevent preprocessing leakage", "Preserve inference transformations",
                       "Audit rare-event metrics", "Compute positive-class recall", "Sequence a monitored promotion"],
        "questions": [
            code_task(
                "Fit preprocessing using only training features. Enter the variable name.",
                "scaler.fit(", ")\nX_train_scaled = scaler.transform(X_train)\nX_valid_scaled = scaler.transform(X_valid)",
                "X_train", "Fit transformation parameters only on training data. Validation and test data are transformed with those fitted parameters.",
                "preprocessing leakage"),
            architecture_task(
                "Place the versioned transformation used during training before model inference.",
                ["Validated features", "", "Registered classifier", "Prediction"], 1,
                ["Fit a new scaler per request", "Use validation labels", "Saved preprocessing pipeline", "Random feature order"], 2,
                "The saved pipeline preserves feature order, encodings and scaling. Refitting on individual requests changes the input contract.",
                "inference consistency"),
            evidence_task(
                "Mark both findings that invalidate this claimed evaluation.",
                "Synthetic audit of a model with 1% positive examples. Inspect methodology, not just the headline accuracy.",
                ["99% accuracy, but positive-class recall is 0%", "Scaler fitted on combined training and test records",
                 "Final test split reserved before model selection", "Feature availability checked against prediction time"],
                [0, 1], "Zero recall shows the headline accuracy hides failure on the target class. Fitting on test rows leaks held-out information.",
                "evaluation audit"),
            code_task(
                "There are 30 true positives and 20 false negatives. Enter recall as a decimal between 0 and 1.",
                "tp = 30\nfn = 20\nrecall = ", "\n# recall = tp / (tp + fn)",
                "0.6", "Recall is 30 / (30 + 20) = 0.6. False positives belong in precision's denominator, not recall's.",
                "recall calculation"),
            sequence_task(
                "Arrange the model promotion workflow.",
                "Register only a reproducible candidate that passes held-out evaluation; canary precedes broad exposure.",
                ["Canary with monitored predictions", "Validate candidate against held-out criteria",
                 "Promote only after monitored acceptance", "Register model, preprocessing and data/code versions"],
                [1, 3, 0, 2],
                "Evaluate independently, register reproducible artifacts, stage exposure and promote only after acceptance checks. Retain a rollback version.",
                "model promotion"),
        ],
    },
    {
        "career": "deep-learning", "title": "Vision model training desk",
        "scenario": "A small image classifier overfits and must later fit a device memory budget. "
                    "Repair a training step, reason about tensor dimensions, inspect experiment traces, "
                    "assemble inference architecture and order compression validation. No neural model is executed.",
        "objectives": ["Repair gradient lifecycle", "Calculate a classifier output shape", "Recognize overfitting",
                       "Place inference preprocessing", "Validate compression on target hardware"],
        "questions": [
            code_task(
                "Clear accumulated gradients before backpropagation. Enter the optimizer method name.",
                "optimizer.", "()\nlogits = model(images)\nloss = criterion(logits, labels)\nloss.backward()\noptimizer.step()",
                "zero_grad", "PyTorch accumulates gradients by default. Clear them before a fresh step unless intentional gradient accumulation is configured.",
                "gradient lifecycle"),
            code_task(
                "A batch of 16 images is classified into 7 mutually exclusive classes. Enter the second logits dimension.",
                "# logits shape = (16, ", ")\nloss = cross_entropy(logits, labels)",
                "7", "A single-label classifier outputs one logit per class per example, so the shape is (16, 7).",
                "output dimensions"),
            evidence_task(
                "Mark the two observations that support an overfitting diagnosis.",
                "Synthetic epochs 5 to 15; training and validation use fixed, disjoint datasets.",
                ["Training loss falls from 0.6 to 0.1", "Validation loss rises from 0.7 to 1.3",
                 "Validation preprocessing is deterministic", "Class names are unchanged"],
                [0, 1], "The paired divergence suggests overfitting. Inspect data quality too, then consider augmentation, regularization or early stopping.",
                "training diagnostics"),
            architecture_task(
                "An image model expects the same resize and normalization as training. Fill the inference gap.",
                ["Raw image", "", "Frozen model in evaluation mode", "Class scores"], 1,
                ["Unrecorded random transformations", "Versioned resize and normalization", "Test-label lookup", "Optimizer update"], 1,
                "Use the recorded preprocessing contract and evaluation mode. Inference must not use labels or change the model's trainable weights.",
                "vision serving"),
            sequence_task(
                "Order a quantization experiment for deployment.",
                "First establish a baseline; evaluate quality and hardware behavior before deployment approval.",
                ["Measure held-out quality and target-device latency/memory", "Quantize a versioned candidate",
                 "Approve or reject against predefined limits", "Record baseline model quality and resource use"],
                [3, 1, 0, 2],
                "Compare a versioned compressed model against a measured baseline. Quality and speed are empirical and hardware-dependent.",
                "compression validation"),
        ],
    },
    {
        "career": "ai-engineering", "title": "Grounded assistant launch",
        "scenario": "Build a document assistant for a university. Assemble retrieval architecture, repair "
                    "its access scope, examine synthetic grounding failures, order a guarded tool workflow "
                    "and calculate a release acceptance threshold. No external model or private document is contacted.",
        "objectives": ["Retrieve authorized evidence", "Bind access to the authenticated principal",
                       "Audit unsupported answers", "Control tool execution", "Apply an evaluation threshold"],
        "questions": [
            architecture_task(
                "Add the retrieval stage before generation.",
                ["Question + authenticated scope", "", "Source-grounded generation", "Cited answer"], 1,
                ["Unfiltered private index", "Authorized document retrieval", "Execute document instructions", "Invent citations"], 1,
                "Retrieve only authorized sources before adding content to context. Grounding and citations still require evaluation.",
                "grounded architecture"),
            code_task(
                "Supply the authenticated principal, not a model-provided user ID. Enter the expression.",
                "documents = retrieve(query=question, user=", ")\n# Permissions are enforced by retrieve().",
                "request.user", "The server-authenticated principal determines permissions. Neither generated text nor a client-supplied owner ID can grant access.",
                "retrieval scope"),
            evidence_task(
                "Mark the two responses that fail grounding or access requirements.",
                "Synthetic audit: sources are authorized policy documents; a missing policy must be reported as unknown.",
                ["Answer cites an existing paragraph that supports its claim", "Answer invents a policy absent from all retrieved sources",
                 "Answer includes a paragraph from another student's restricted file", "Answer states that evidence was not found"],
                [1, 2], "Fabricated claims and unauthorized content fail the evaluation. A clear evidence gap is preferable to a confident unsupported answer.",
                "grounding review"),
            sequence_task(
                "Order a controlled tool request.",
                "The model proposes a timetable lookup; the application independently validates and authorizes it.",
                ["Execute the narrowly scoped read-only tool", "Validate structured arguments",
                 "Return a minimal result for the grounded reply", "Authorize the lookup against the signed-in user"],
                [1, 3, 0, 2],
                "Validate arguments, enforce authorization, execute only the permitted read and return minimal data. Model suggestions are not authorization.",
                "tool workflow"),
            code_task(
                "The release gate requires at least 95 grounded answers out of 100. Enter the minimum accepted count.",
                "grounded_count = evaluate(held_out_cases)\nrelease_allowed = grounded_count >= ", "\n",
                "95", "The numerical threshold is 95 for this synthetic policy. Access-boundary failures should have their own blocking gate, not be averaged away.",
                "evaluation gates"),
        ],
    },
    {
        "career": "data-science", "title": "Attendance experiment review",
        "scenario": "A reminder experiment appears to raise attendance. Repair the analysis query, "
                    "place the validated dataset, inspect synthetic report evidence, compute the absolute "
                    "effect and order a reproducible report. No real learner records are used.",
        "objectives": ["Count unique participants", "Validate join cardinality", "Identify analytical defects",
                       "Calculate an absolute effect", "Sequence reproducible reporting"],
        "questions": [
            code_task(
                "Count unique students after a one-to-many attendance join. Enter the SQL keyword.",
                "SELECT COUNT(", " student_id)\nFROM attendance\nWHERE attended = TRUE;",
                "DISTINCT", "COUNT(DISTINCT student_id) avoids counting the same student once per attendance record. Define the cohort and period explicitly.",
                "analytical sql"),
            architecture_task(
                "Validate the data before computing experiment outcomes.",
                ["Versioned attendance + assignment snapshots", "", "Per-participant outcome", "Group comparison"], 1,
                ["Blind many-to-many join", "Validated participant-key join", "Duplicate every control row", "Discard assignment IDs"], 1,
                "Check participant identifiers and expected cardinality before aggregation so joins do not alter denominators or treatment assignment.",
                "analysis pipeline"),
            evidence_task(
                "Mark both defects in the proposed report.",
                "Synthetic review of a randomized reminder experiment with a prespecified participant cohort.",
                ["Unmatched attendance is treated as confirmed absence without investigation",
                 "The treatment cohort excludes nonresponders after assignment",
                 "Group denominators and outcome windows are reported",
                 "Randomization and prespecified inclusion rules are documented"],
                [0, 1], "Missing records need interpretation; excluding participants based on post-assignment response can bias the comparison.",
                "experiment audit"),
            code_task(
                "Treatment attendance is 72% and control attendance is 65%. Enter the absolute increase in percentage points.",
                "treatment_percent = 72\ncontrol_percent = 65\nabsolute_effect_pp = ", "\n",
                "7", "72 - 65 = 7 percentage points. This is not a 7% relative increase; the relative increase would be 7 / 65.",
                "effect size"),
            sequence_task(
                "Order the reproducible reporting workflow.",
                "Freeze inputs before analysis and verify uncertainty before communicating conclusions.",
                ["Communicate estimates, uncertainty and limitations", "Freeze dataset snapshots and prespecified cohort",
                 "Validate outcome calculations and uncertainty", "Run versioned cleaning, joins and analysis"],
                [1, 3, 2, 0],
                "Record inputs and cohort, run reproducible transformations, validate estimates and uncertainty, then communicate limitations.",
                "reproducible reporting"),
        ],
    },
    {
        "career": "full-stack", "title": "Last-seat booking release",
        "scenario": "Two learners compete for the final course seat. Repair a reservation boundary, "
                    "place a concurrency-safe database step, inspect synthetic access logs, repair an "
                    "idempotency header and order a compatible deployment. Code fragments are evaluated, never executed.",
        "objectives": ["Enforce booking ownership", "Protect seat consistency", "Audit access defects",
                       "Reuse operation identity on retries", "Sequence an expand-and-contract release"],
        "questions": [
            code_task(
                "Bind a booking lookup to the signed-in student. Enter the expression.",
                "booking = get_object_or_404(Booking, id=booking_id, student=", ")\n",
                "request.user", "Object access must be scoped to the authenticated user. Hiding another booking's link is not an authorization check.",
                "booking ownership"),
            architecture_task(
                "Make the final-seat check and reservation atomic under concurrent requests.",
                ["Validated booking request", "", "Persist reservation + decrement seats", "Commit + return result"], 1,
                ["Browser-only seat check", "Transaction with appropriate row lock", "Read from stale local storage", "Unbounded client retries"], 1,
                "A transaction with appropriate locking or a conditional atomic update ensures only an eligible request takes the final seat.",
                "reservation consistency"),
            evidence_task(
                "Mark the two server observations that are verified defects.",
                "Synthetic log review. Students may only read their own bookings; inventory starts with one remaining seat.",
                ["student=B GET booking(owner=A) -> 200", "Concurrent requests both reserve the final seat",
                 "Unauthenticated booking request -> 401", "Owner reads their own confirmed booking -> 200"],
                [0, 1], "Cross-owner access violates authorization, and two reservations for one seat violate concurrency invariants.",
                "release investigation"),
            code_task(
                "The API contract uses this exact HTTP header for a stable retry identifier. Enter its name.",
                "fetch('/api/bookings/', {\n  method: 'POST',\n  headers: {'", "': operationId},\n  body: JSON.stringify(booking)\n});",
                "Idempotency-Key", "Reuse the same operation key for retries of the same logical booking. The server must atomically enforce uniqueness and persist the outcome.",
                "idempotent requests"),
            sequence_task(
                "Arrange the expand-and-contract deployment.",
                "Old and new instances briefly coexist. Remove the old schema only after all readers and writers stop using it.",
                ["Remove obsolete schema after old instances retire", "Add backward-compatible schema",
                 "Backfill data and verify consistency", "Deploy code that supports old and new representations"],
                [1, 3, 2, 0],
                "Expand first, deploy compatible code, backfill with checks, then contract when old usage is gone. Plan recovery before each stage.",
                "compatible delivery"),
        ],
    },
]
