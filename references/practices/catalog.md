# Engineering practice catalog

Use this catalog for a concrete project choice. These are reference sources and selectable practices, not a universal checklist. Explain the applicable scope, benefit, cost, tailoring and verification in the project's engineering baseline. Consult official current details before relying on version-sensitive provisions. Do not claim certification or full conformance from adopting selected ideas.

## Knowledge and quality

**SWEBOK — coverage of engineering concerns.** Use when framing a substantial project or checking whether requirements, design, construction, testing and maintenance concerns have been overlooked. It is a knowledge map, not a required sequence of documents. Tailor to the current scope. Check that relevant concerns are addressed, not that every knowledge area has a file. Source: [IEEE Computer Society](https://www.computer.org/education/bodies-of-knowledge/software-engineering).

**ISO/IEC 25010 — quality goals.** Use when "good quality" needs to become meaningful requirements. Select relevant attributes and scenarios; justify measurements and trade-offs. Do not manufacture thresholds or claim adherence to the full paid standard from its abstract. Check selected goals against actual scenarios/evidence. Source: [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html).

## Architecture and interfaces

**Information hiding and cohesive responsibilities.** Useful when multiple changes or integrations need stable boundaries. Organize around decisions/reasons to change, expose what consumers need, and assess dependency impact. Extra interfaces or layers add cost; introduce them for meaningful variation or responsibility separation. Check actual change locality, contracts and dependency direction. Source: [Parnas, On the Criteria To Be Used in Decomposing Systems into Modules](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html).

**arc42 — architecture views.** Useful when maintainers need a common picture of scope, structure, runtime interactions, deployment or cross-cutting mechanisms. Select the views that explain this system; a small project need not fill twelve sections. Check that diagrams and text agree and answer stakeholder questions. Source: [arc42 overview](https://arc42.org/overview/).

**Ports and adapters — external variation.** Useful for replacing external services or testing behavior independently of technology. The seam and adapter maintenance are costs; do not impose a hexagon or five directories on every module. Check that the intended dependency is replaceable and domain behavior remains comprehensible. Source: [Cockburn](https://alistair.cockburn.us/hexagonal-architecture).

## Language and repository

**Language style, exemplified by PEP 8.** Use the relevant language/community guidance together with existing project configuration. Project-specific conventions can tailor general guidance; do not break compatibility merely for style. Check the configured formatter/linter plus naming/readability where tooling cannot decide. Source: [PEP 8](https://peps.python.org/pep-0008/).

**Package organization, exemplified by PyPA.** Relevant to installable Python code or import/build ambiguity. Consider src vs flat layout and packaging needs; a disposable script does not require library scaffolding. Check the intended installed/imported behavior, not just execution from the repository root. Source: [Python Packaging User Guide](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).

## Verification and review

**Behavior-oriented tests and focused changes.** Derive expectations independently of the implementation; select unit, integration or end-to-end checks according to the changed behavior. TDD is an optional development strategy, not a universal gate. Test infrastructure and broad suites have maintenance cost. Check meaningful failure sensitivity and integration behavior, and inspect design/complexity as well as test success. Sources: [Google review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html), [small changes](https://google.github.io/eng-practices/review/developer/small-cls.html).

**Standards and specification review.** Report engineering-convention findings separately from missing/wrong/extra requirements. A style-compliant implementation can still implement the wrong thing. Treat heuristic smells as judgments, not hard violations. Independent reviewers are useful where justified and authorized, not mandatory for every fix. Inspiration: [Matt Pocock code-review, pinned source](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/code-review/SKILL.md).

## Documentation and delivery

**Diátaxis — consumer documentation.** Use when readers need tutorials, how-to guides, reference or explanation. Select by reader need; these categories do not replace requirements/design/decision/verification records. Avoid empty scaffolding. Check that the user can find the relevant learning or operational answer. Source: [Diátaxis](https://diataxis.fr/).

**Decision rationale.** Preserve context, choice and consequences for consequential decisions. Our default is an append-only Markdown log with optional detailed records; it does not require one ADR file for every decision. Check provenance and superseding links. Source: [Nygard on architecture decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

**Semantic Versioning — declared public API compatibility.** Relevant where consumers rely on versioned public contracts. Establish what the public API is before applying version rules. Release discipline adds overhead and does not substitute for compatibility testing. Check observed changes against the selected version policy. Source: [Semantic Versioning](https://semver.org/).

## Selection boundaries

The catalog is curated, not exhaustive. Add specialized safety, security, accessibility, reproducibility or operations practices when actual requirements warrant them, with primary sources and explicit applicability. Reuse existing project choices; conflicts with human intent or material constraints need a supported decision, not silent imposition of a catalog preference.
