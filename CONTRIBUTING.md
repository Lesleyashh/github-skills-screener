**Contributing**

================

Thanks for your interest in contributing to the Evidence-Based GitHub User Screener.

This project is intentionally **configuration-driven**. New job roles, candidates, and screening criteria are added through configuration files rather than by editing application code.

* * * * *

**Adding a new job role**

-------------------------

Follow the steps below to add a new job role and run a screening.

### **1\. Choose a job and define its job_id**

Select the role you want to screen for and record its **business-defined job ID**, for example:

JOB_ID="org-67890"

This identifier is used consistently throughout the system.

* * * * *

### **2\. Create the job role configuration directory**

Create a directory for the job role under config/job_roles/:

mkdir -p "config/job_roles/${JOB_ID}"

Example:

mkdir -p "config/job_roles/org-67890"

* * * * *

### **3\. Create the job_skills.json file from the template**

Copy the template file and edit the values as needed:

cp config/job_roles/_template/job_skills.example.json

config/job_roles/${JOB_ID}/job_skills.json

Ensure that:

-   job_id in the file matches the directory name

-   Required and optional skills exist in config/skills_catalog.json

-   Increment the version if criteria change

* * * * *

### **4\. Create the candidate input directory**

Candidate input is stored separately from configuration:

mkdir -p "candidate_input/job_roles/${JOB_ID}"

* * * * *

### **5\. Create the usernames.txt file**

Create the usernames file from the example:

cp -n candidate_input/job_roles/${JOB_ID}/usernames.example.txt

candidate_input/job_roles/${JOB_ID}/usernames.txt

Notes:

-   One GitHub username per line

-   Blank lines are ignored

-   Lines starting with # are treated as comments

* * * * *

### **Running the scan**

Once configured, you can run the scan:

make scan JOB_ID=${JOB_ID}

Example:

make scan JOB_ID=org-67890

View results:

make report JOB_ID=${JOB_ID}

Export results to CSV:

make export JOB_ID=${JOB_ID}

* * * * *

**Skills and evidence**

-----------------------

High-level skills are defined in:

config/skills_catalog.json

Each skill maps to one or more **low-level evidence signals**, which define how skills are detected based on file presence. These live in:

config/skills_evidence_catalog.json

When adding new skills or evidence signals:

-   Prefer file presence over keyword scanning

-   Keep rules conservative to avoid false positives

-   Ensure skills are referenced consistently across catalogs and job configs

* * * * *

**Code changes**

----------------

Code contributions are welcome but should be small, focused, and covered by tests where appropriate.

Before contributing code, run:

make lint

make test

* * * * *

**Data and privacy**

--------------------

-   Do not commit real candidate data

-   usernames.txt, generated reports, and the SQLite database must remain untracked

-   The tool evaluates only public GitHub data provided with explicit opt-in

* * * * *

**Testing expectations**

------------------------

-   Unit tests must pass before opening a PR

-   Integration tests require a valid GITHUB_TOKEN

-   New features should include unit test coverage

* * * * *

**Raising a Pull Request**

--------------------------

Contributions are welcome via pull request.

### **Before opening a PR**

-   Create a feature branch from dev

-   Keep changes focused and scoped

-   Run tests locally:

make test-unit

### **Review principles**

-   Changes should favour clarity and explainability

-   Matching logic should remain simple and auditable

-   This tool supports hiring decisions; it does not automate them

Approved PRs are merged into dev and promoted to main once stable.
