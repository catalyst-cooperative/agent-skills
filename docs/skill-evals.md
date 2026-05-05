---
icon: lucide/check
---

# Agent Skill Evals

## What are we evaluating?

In general the outcome of skill evaluations will be a function of multiple factors, including:

- The underlying model (e.g. Gemma 4, Claude Sonnet 4.6, GPT 5.4), which determines the fundamental capabilities and limitations of the agent
- The agent harness (e.g. Pi, Claude Code, VS Code Co-pilot chat), which determines how the model interacts with tools, files, web search, and the environment
- The skill definition, which provides dynamic model context including code snippets and workflow outlines
- Other contextual factors like the specific prompt given to the agent, the agent's prior interactions in the conversation, and other files or information available to the agent in the environment.

With the `datapackage` and `pudl` skills in particular, the outcome will also depend on:

- The metadata, data, and associated documentation being queried, which may vary in quality and quantity.
    For datapackages in general, we will have no control over this input, and should use both ideal and real-world examples for testing.
    For PUDL in particular, we control the metadata, data, and documentation, and so can choose to either make changes to the skill, or the input to try and improve outcomes.

When we're evaluating skill performance we want to be intentional about the state of the other factors we can control.
In some cases (e.g. choice of model and harness) we'll want to test a handful of common configurations.
In others (e.g. context leakage from outside the conversation) we'll want to try and minimize the impact and collect actual user feedback from the real world.

## Context Leakage

- We don't want to accidentally provide the agent with too much context or information from outside of the skill that real world users would not have.
- For example, an adjacent checkout of the PUDL repo with all of our documentation in it, or the development files that exist in the `agent-skills` repo but which won't be distributed with the skill when it's installed by users.
- To avoid context leakage from outside the repo, we can run the evals inside a containerized sandbox.
- To avoid context leakage from previous interactions, we can reset the agent's state between evals.
- To avoid context leakage from development files in the `agent-skills` repo, we can remove those files from the skill definition directory.
- To more robustly avoid context leakage from elsewhere in the `agent-skills` repo entirely and see what a real-world install looks like, we can get the skill to where it's installable with `npx skills add` and install it into the sandbox.

## Model / Harness Configurations

- **Open Stack:** Gemma 4 26B A4B in the Pi TUI -- a cheap, capable open model that can be run locally, plus an extensible minimalist open source TUI harness, to make sure we are supporting the open source ecosystem.
    This configuration will be cheap to test, but performance may not be indicative of what users will experience with more capable models and harnesses.
- **Anthropic:** Claude Sonnet 4.6 in Claude Code Desktop -- this seems like it may be the most common current setup that users doing analysis but not software development are currently using.
- **Microsoft:** GPT 5.4 in the VS Code Co-pilot Chat -- a common configuration for users that do software development.

## How good is good enough?

- We need to evaluate whether the skill is working **well enough** for us to feel comfortable deploying and publicizing it.
- Whether it works well enough will probably depend strongly on the capabilities of the model being used.
- We also need to know if changes we make improve or degrade performance relative to a previous baseline.
- The directional change in performance might be discernible even with a smaller or less capable model whose absolute performance isn't great.
