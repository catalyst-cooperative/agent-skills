# [Catalyst Cooperative](http://github.com/catalyst-cooperative) Agent Skills

This repository contains experimental [agent skills](https://agentskills.io) related to PUDL (the Public Utility Data Liberation Project).

- `datapackage` provides agents context on how to work with the [Frictionless Datapackage](https://datapackage.org/) metadata standard
- `pudl` is for exploring and working with [PUDL open energy data and metadata](https://data.catalyst.coop)

## Installing

Most LLM agents support skills, but depending on the agent there are many different ways that skills are installed and activated.
One fairly generic, agent-agnostic method of installing them is `npx skills`.
If you have `npm` installed you should be able to do:

```bash
npx skills install catalyst-cooperative/agent-skills -s datapackage
npx skills install catalyst-cooperative/agent-skills -s pudl
npx skills install catalyst-cooperative/agent-skills -s pudl-dev
```

## Agent Skills Resources

### For Users

- [Using Agent Skills in VS Code](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
- [Extend Claude with Agent Skills](https://code.claude.com/docs/en/skills)
- [npx skills](https://github.com/vercel-labs/skills) (CLI for installing skills)
- [Agent Skill Installation CLI](https://www.npmjs.com/package/skills)
- ⚠️ [The Agent Skills Directory](https://skills.sh/) ⚠️

### For Skills Authors

- [The Agent Skills Standard](https://agentskills.io)
- [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Equipping Agents for the Real World With Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Developer Guide Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Create a Claude Plugin Marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)

## Agentic (Data) Engineering

- [Agentic Engineering Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/) (Simon Willison)
- [Zero Degree-of-Freedom LLM Coding using Executable Oracles](https://john.regehr.org/writing/zero_dof_programming.html) (John Regehr)
- [Dagster University AI Driven Data Engineering](https://courses.dagster.io/courses/take/ai-driven-data-engineering) (Dagster)
- [Best practices for LLM Dagster Development](https://www.youtube.com/watch?v=nmuQPU9bzQ4) (Dagster)
- [What Is Code Review For](https://blog.glyph.im/2026/03/what-is-code-review-for.html) (Glyph)
- [Your job is to deliver code you have proven to work](https://simonwillison.net/2025/Dec/18/code-proven-to-work/) (Simon Willison)

## Agentic (Meta)Data Exploration

- [Coding agents for data analysis](https://simonw.github.io/nicar-2026-coding-agents/) (Simon Willison)

## Other related skills

Agent skills defined outside of this repo that we either used in creating the Catalyst
Cooperative agent skills, or that we delegate to within the skill.

- [duckdb-skills](https://github.com/duckdb/duckdb-skills)
- [marimo-pair](https://github.com/marimo-team/marimo-pair)
- [skill-creator](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator)
- [dignified-python](https://github.com/dagster-io/skills/tree/main/plugins/dignified-python)
