"""Curated demo lessons and quizzes; answer keys stay on the server."""

MISSIONS = {
    "angular": [
        "Your first assignment is a student profile screen. The designer needs a reusable "
        "greeting component and an accessible form. Review the proposed implementation "
        "before your teammate connects it to real student data.",
        "A career search page consumes a remote API. Students type quickly and sometimes "
        "lose connectivity. Review the data flow and service boundaries so the interface "
        "stays consistent when requests finish out of order.",
        "Your team is preparing a production release of a learning dashboard. Review "
        "performance, state updates and test coverage. Decide which changes protect "
        "maintainability without hiding defects behind a fast-looking demo.",
    ],
    "cloud": [
        "A small training center wants to host its first web platform. You join the "
        "infrastructure planning meeting. Compare deployment choices and identify "
        "which responsibilities remain with the team.",
        "Registrations increase and the platform must handle more demand. Review the "
        "proposed architecture, balancing availability and resource limits. Choose "
        "changes that keep the service observable and recoverable.",
        "A production service must survive failures without losing student progress. "
        "You participate in an operations review covering automation, resilience and "
        "delivery practices. Decide what evidence is needed before the next release.",
    ],
    "cybersecurity": [
        "You help onboard students to a learning platform. The support team needs "
        "guidance on protecting accounts and handling suspicious messages. Review "
        "the proposed safeguards before the onboarding guide is published.",
        "A team is reviewing how its web platform accepts input and exposes private "
        "student records. Assess its defensive controls and choose changes that "
        "reduce risk without relying on frontend-only checks.",
        "You join a defensive security readiness review. The team must detect unusual "
        "activity, protect sensitive access and respond responsibly. Evaluate proposed "
        "controls and distinguish useful evidence from unsupported assumptions.",
    ],
}

CAREERS = [
    {
        "slug": "angular",
        "title": "Angular Developer",
        "summary": "Build accessible, maintainable web interfaces with Angular and TypeScript.",
        "description": "Angular developers translate product requirements into component-based applications, integrate APIs, and test user-facing features.",
        "category": "Software development",
        "tools": ["Angular", "TypeScript", "RxJS", "Node.js"],
        "interests": ["web development", "design", "programming"],
        "salary": "Varies by country, experience and employer; consult local salary surveys.",
        "education": "Computer science degree or equivalent portfolio and practical training.",
        "outlook": "Enterprise web applications need maintainable front-end engineering.",
        "levels": [
            ("Component foundations", [
                (
                    "Which Angular mechanism passes a value from a parent into a child component?",
                    ["An input property", "A CSS selector", "A database migration", "A browser cookie"],
                    [0], "components",
                    "An input property defines a component's parent-to-child data contract.",
                    "readonly title = input.required<string>();",
                ),
                (
                    "A template must display the current user's name. Which syntax interpolates a value?",
                    ["{{ user.name }}", "# user.name #", "SELECT user.name", "<script>user.name</script>"],
                    [0], "templates",
                    "Interpolation with double braces renders an expression as text; avoid injecting HTML for plain names.",
                    "<h1>Hello {{ user.name }}</h1>",
                ),
                (
                    "Which practices improve an Angular form's accessibility? Select all that apply.",
                    ["Associate labels with inputs", "Use native buttons for actions", "Use color as the only error indicator", "Remove keyboard focus outlines everywhere"],
                    [0, 1], "accessibility",
                    "Labels and native controls support assistive technology and keyboard use. Errors also need textual meaning.",
                    '<label for="email">Email</label><input id="email" type="email">',
                ),
            ]),
            ("Reactive data and services", [
                (
                    "Where should shared API access normally live instead of being copied across components?",
                    ["An injectable service", "Every template", "A global CSS file", "A database trigger in the browser"],
                    [0], "architecture",
                    "An injectable service centralizes API behavior and can be replaced by a test double.",
                    "@Injectable({providedIn: 'root'}) export class CareerService {}",
                ),
                (
                    "A search box emits new terms while earlier HTTP searches are pending. Which RxJS operator switches to the latest request?",
                    ["switchMap", "concatMap", "count", "toArray"],
                    [0], "reactive programming",
                    "switchMap unsubscribes from the previous inner observable, so stale searches do not overwrite newer results.",
                    "terms.pipe(debounceTime(250), distinctUntilChanged(), switchMap(term => api.search(term)))",
                ),
                (
                    "Which practices help avoid observable subscription leaks? Select all that apply.",
                    ["Use the async pipe in templates", "Use takeUntilDestroyed in component subscriptions", "Subscribe in every change-detection cycle", "Keep subscriptions forever after destruction"],
                    [0, 1], "resource management",
                    "The async pipe and lifecycle-bound cleanup release subscriptions when their consumers are destroyed.",
                    "service.items$.pipe(takeUntilDestroyed()).subscribe(items => this.items = items);",
                ),
            ]),
            ("Production quality", [
                (
                    "Which approach helps Angular identify stable list items when the array is refreshed?",
                    ["Track items by a stable unique ID", "Track every item by a random number", "Recreate every component deliberately", "Disable all rendering"],
                    [0], "performance",
                    "Stable tracking keys allow Angular to reuse the right DOM nodes during list updates.",
                    "@for (career of careers(); track career.id) { <p>{{ career.title }}</p> }",
                ),
                (
                    "Which test isolates a component from real backend availability?",
                    ["Provide a mock API service", "Call production APIs in every unit test", "Turn off assertions", "Only check that the file exists"],
                    [0], "testing",
                    "Mock services make component tests deterministic; separate integration tests exercise the real API boundary.",
                    "providers: [{provide: CareerService, useValue: fakeCareerService}]",
                ),
                (
                    "Which controls protect a privileged operation? Select all that apply.",
                    ["Check authorization on the server", "Validate input on the server", "Hide a button as the only authorization check", "Trust a role sent in the request body"],
                    [0, 1], "security",
                    "Route guards and hidden buttons improve UX, not security. Servers must authorize operations and validate data.",
                    "A server rejects editing another user's record even if a forged browser request reaches it.",
                ),
            ]),
        ],
    },
    {
        "slug": "cloud",
        "title": "Cloud Engineer",
        "summary": "Design reliable cloud infrastructure and automate safe deployments.",
        "description": "Cloud engineers operate compute, storage and networking, manage access, and improve reliability through monitoring and repeatable infrastructure.",
        "category": "Infrastructure",
        "tools": ["AWS or Azure", "Terraform", "Docker", "Linux"],
        "interests": ["automation", "infrastructure", "distributed systems"],
        "salary": "Varies by country, experience and employer; consult local salary surveys.",
        "education": "Networking and Linux foundations with cloud projects or relevant certifications.",
        "outlook": "Cloud adoption creates demand for reliable, cost-aware platform operations.",
        "levels": [
            ("Cloud foundations", [
                (
                    "Which cloud service is best suited to storing image files as objects?",
                    ["Object storage", "A message queue", "A CPU scheduler", "A DNS record"],
                    [0], "storage",
                    "Object storage stores files with keys and metadata and scales without maintaining a filesystem server.",
                    "Store an image under the key profiles/user-42/avatar.png in a private bucket.",
                ),
                (
                    "What does least privilege mean for a deployment identity?",
                    ["Only grant permissions required for its tasks", "Grant administrator access by default", "Share root credentials", "Disable all auditing"],
                    [0], "identity",
                    "Scoped identities reduce the impact of compromised credentials and accidental actions.",
                    "Allow the deployment role to update one application, not every account resource.",
                ),
                (
                    "Which design choices improve availability? Select all that apply.",
                    ["Deploy across independent availability zones", "Use health checks to remove unhealthy instances", "Keep all replicas on one host", "Store backups only on the source disk"],
                    [0, 1], "availability",
                    "Independent failure domains and health-aware routing reduce the impact of a host or zone outage.",
                    "A load balancer routes requests to healthy replicas in two availability zones.",
                ),
            ]),
            ("Infrastructure automation", [
                (
                    "Why review a Terraform plan before applying it?",
                    ["To inspect intended resource changes", "To encrypt every response", "To replace all backups", "To guarantee zero downtime automatically"],
                    [0], "infrastructure as code",
                    "A plan shows additions, updates and deletions so reviewers can catch destructive or unexpected changes.",
                    "terraform plan -out=reviewed.plan",
                ),
                (
                    "Which configuration helps a container run with reduced privilege?",
                    ["Run as a non-root user", "Use --privileged by default", "Mount the host root filesystem writable", "Put cloud keys in the image"],
                    [0], "containers",
                    "A non-root process limits capabilities; secrets should be supplied separately at runtime.",
                    "USER 10001",
                ),
                (
                    "Which practices protect infrastructure state? Select all that apply.",
                    ["Use encrypted remote state with access controls", "Enable state locking", "Commit plaintext state secrets publicly", "Let every operator overwrite state concurrently"],
                    [0, 1], "state management",
                    "State can contain secrets. Encryption, access controls and locking protect confidentiality and consistency.",
                    "Use a private remote backend with encryption and locking enabled.",
                ),
            ]),
            ("Reliability and operations", [
                (
                    "Which metric best reflects a user's experience of a slow API?",
                    ["Request latency percentiles", "The number of source files", "The color of a dashboard", "The version of the editor"],
                    [0], "observability",
                    "Tail latency such as p95 reveals delays that averages can hide and supports user-facing service objectives.",
                    "Track p95 request latency and alert when the latency objective burns error budget.",
                ),
                (
                    "What is the purpose of a canary deployment?",
                    ["Expose a small traffic share before wider rollout", "Deploy all instances simultaneously without monitoring", "Disable rollback", "Avoid testing completely"],
                    [0], "delivery",
                    "A canary limits blast radius and compares operational signals before broad deployment.",
                    "Route 5% of requests to the new version and roll back if error rate increases.",
                ),
                (
                    "Which steps support recovery from a database outage? Select all that apply.",
                    ["Test restoring backups", "Define recovery time and recovery point objectives", "Assume a successful backup guarantees restore", "Store the only recovery key on the failed host"],
                    [0, 1], "disaster recovery",
                    "Restore drills verify usable backups. RTO and RPO specify acceptable downtime and data loss.",
                    "Run a restore drill and record whether recovery meets the agreed RTO and RPO.",
                ),
            ]),
        ],
    },
    {
        "slug": "cybersecurity",
        "title": "Cybersecurity Analyst",
        "summary": "Protect systems with risk analysis, secure defaults and incident response.",
        "description": "Cybersecurity analysts identify threats, investigate alerts, strengthen access controls and help organizations prevent and recover from incidents.",
        "category": "Security",
        "tools": ["SIEM", "Wireshark", "Linux", "Identity platforms"],
        "interests": ["security", "investigation", "networks"],
        "salary": "Varies by country, experience and employer; consult local salary surveys.",
        "education": "Security and networking foundations with ethical practical labs or certifications.",
        "outlook": "Organizations need continuous monitoring and incident readiness.",
        "levels": [
            ("Security foundations", [
                (
                    "Which control improves account security beyond a password?",
                    ["Multi-factor authentication", "Password reuse", "Sharing login credentials", "Disabling session expiry"],
                    [0], "identity",
                    "A second independent factor reduces the value of a stolen password; phishing-resistant factors offer stronger protection.",
                    "Require a security key for privileged sign-in.",
                ),
                (
                    "A suspicious email asks for your password through an unexpected link. What is the safest response?",
                    ["Report it and verify using a trusted independent channel", "Enter credentials to test the page", "Forward it to everyone", "Download its attachment"],
                    [0], "threat awareness",
                    "Independent verification avoids trusting the sender's link, and reporting supports organization-wide response.",
                    "Open the known official site directly rather than following the email link.",
                ),
                (
                    "Which actions reduce unnecessary exposure? Select all that apply.",
                    ["Patch supported software promptly", "Disable unused services", "Expose every port publicly", "Use a shared administrator account"],
                    [0, 1], "hardening",
                    "Patching reduces known weaknesses, and removing unused services shrinks the attack surface.",
                    "Inventory services, remove unused listeners, and apply tested updates.",
                ),
            ]),
            ("Application and network defense", [
                (
                    "Which database practice prevents user input from being interpreted as SQL syntax?",
                    ["Parameterized queries", "String concatenation with raw input", "Removing spaces only", "Client-side validation only"],
                    [0], "application security",
                    "Parameters keep user values separate from query structure; client-side controls cannot enforce server safety.",
                    'cursor.execute("SELECT id FROM users WHERE email = %s", [email])',
                ),
                (
                    "Why must a session-authenticated web API validate CSRF tokens on unsafe requests?",
                    ["Browsers attach session cookies to requests, including forged requests", "CSRF tokens replace authentication", "TLS disables all cross-site requests", "GET requests must always change data"],
                    [0], "web security",
                    "CSRF protection ensures unsafe browser requests carry an origin-bound token, not just automatically sent cookies.",
                    "Send X-CSRFToken along with same-origin session cookies for POST and PATCH.",
                ),
                (
                    "Which controls limit lateral movement? Select all that apply.",
                    ["Segment networks by trust and purpose", "Restrict service-to-service access", "Permit any host to access every database", "Reuse privileged credentials everywhere"],
                    [0, 1], "network security",
                    "Segmentation and scoped communication paths contain compromise instead of assuming the internal network is safe.",
                    "Only the application subnet may reach the database port.",
                ),
            ]),
            ("Incident response", [
                (
                    "An endpoint shows credible signs of compromise. What is the best initial operational response?",
                    ["Follow the response plan, isolate safely and preserve evidence", "Erase all disks immediately", "Ignore the alert", "Publicly share sensitive logs"],
                    [0], "incident response",
                    "Coordinated containment limits damage while preserving evidence for investigation and recovery.",
                    "Record incident time, notify the response team, and use approved isolation procedures.",
                ),
                (
                    "Which log detail is most useful when correlating an authentication incident across systems?",
                    ["Consistent timestamps and request or identity identifiers", "Random local times without timezone", "Only UI colors", "Only the source file name"],
                    [0], "investigation",
                    "Time synchronization and stable identifiers help reconstruct events across services without exposing credentials.",
                    "Record UTC timestamp, event ID, actor ID and outcome; never log passwords.",
                ),
                (
                    "Which actions belong in post-incident improvement? Select all that apply.",
                    ["Identify root causes and control gaps", "Assign and verify remediation actions", "Blame one individual and stop analysis", "Keep the same exposed credentials"],
                    [0, 1], "risk management",
                    "A blameless review turns evidence into verified improvements and reduces recurrence.",
                    "Document findings, rotate affected credentials, assign owners and validate fixes.",
                ),
            ]),
        ],
    },
]
