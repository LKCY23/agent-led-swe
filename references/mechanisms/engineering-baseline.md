# Engineering baseline

Establish the quality requirements and engineering conventions applicable to the current increment before substantial implementation. A baseline is an explicit working agreement that can evolve with evidence, not a demand to predict every internal detail.

## Form it

1. Inspect project purpose, expected lifetime, consumers, deployment/maintenance context, and explicit human preferences.
2. Read the existing repository guidance, architecture, build/test configuration, and representative code. Separate deliberate conventions from accidental defects or unfinished work.
3. Identify choices material to this increment: architecture and responsibilities, repository organization, interfaces, dependencies, language style, testing, review, compatibility, and documentation as relevant.
4. Consult the [practice catalog](../practices/catalog.md) only for the choices at hand. Explain applicability, cost, and necessary tailoring. A referenced standard is not automatically adopted in full.
5. Record what applies, its scope, why it was selected, and how conformity is checked. Distinguish requirements from recommendations. Resolve consequential conflicts using [human collaboration](human-collaboration.md).

For an existing bounded change, sufficient conventions may already exist. Cite and use them rather than producing another baseline file. For a new substantial project, use the [baseline template](../../assets/templates/engineering-baseline.md) once the relevant choices are settled.

## Apply and check

Translate conventions into engineering choices rather than generic promises such as "clean code." Example: a declared dependency direction constrains imports and composition; a compatibility promise determines which interfaces may change and what checks are needed.

Use suitable automated checks for measurable conventions and actual review for architecture, readability, complexity, and maintainability. A smell is a reason to investigate, not automatically a violation. Test count, file count, coverage percentage, or function length alone does not prove quality.

Check three distinct questions: does behavior work, are requirements/design faithfully implemented, and does the code conform to the engineering baseline? Record evidence and limits for each. Do not invent arbitrary numerical thresholds absent an accepted requirement or justified measurement.

## Evolve it

If a convention conflicts with new requirements or evidence, explain the conflict and consequences. Make consequential changes through the collaboration mechanism. Append the decision, update the current baseline, and identify affected design, code, and verification. Do not silently relax a rule because the current implementation fails it.

Preserve project-specific preferences and useful existing conventions. Avoid imposing a universal architecture, file layout, formatter, test strategy, or dependency just because it appears in the catalog.
