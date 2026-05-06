---
icon: simple/docker
---

# Agent Sandbox

The agent sandbox is a containerized development environment that lets any coding agent work on this repository with full, unrestricted access — safely isolated from your host system.

The container *is* the security boundary. Agents run inside it with all permissions enabled. The worst outcome is a broken container, which is trivially reset with `pixi run devcontainer-rebuild`.

## How it works

The sandbox is built on three components working together:

- **Docker container** — Ubuntu-based, using the [pixi base image](https://github.com/prefix-dev/pixi-docker). The Dockerfile lives at `.devcontainer/Dockerfile`.
- **Bind mount** — The repository root is mounted at `/workspace` inside the container. Edits made inside the container appear on your host immediately, and vice versa. You can use your normal host-side editor while an agent runs inside the container.
- **Named Docker volume** — The pixi environment (`.pixi/`) lives in a separate Docker volume (`agent-skills-pixi`) so that Linux binaries installed inside the container never land on your macOS filesystem.

Agent CLIs (Claude Code, Gemini, Codex, Pi, OpenCode) are installed into the pixi volume during first-time setup and available on `PATH` inside the container.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) — on macOS, [OrbStack](https://orbstack.dev/) is recommended over Docker Desktop
- API keys for the agents you plan to use, exported in your host shell environment (see [API keys](#api-keys) below)

## First-time setup

Build the Docker image and create the named pixi volume:

```bash
pixi run devcontainer-rebuild
```

This only needs to be run once per machine, or after a change to `.devcontainer/Dockerfile`.

## Starting the sandbox

VS Code (and its derivatives like Cursor & Windsurf), Zed, and JetBrains IDEs all support the devcontainer spec natively — follow your IDE's own documentation to open a devcontainer, then come back here for the first-time setup step.

| IDE      | Devcontainer docs                                                                                                              |
| -------- | ------------------------------------------------------------------------------------------------------------------------------ |
| VS Code  | [containers.dev/supporting](https://containers.dev/supporting)                                                                 |
| Cursor   | Same as VS Code — install the Dev Containers extension                                                                         |
| Windsurf | Same as VS Code — install the Dev Containers extension                                                                         |
| Zed      | [zed.dev/docs/dev-containers](https://zed.dev/docs/dev-containers)                                                             |
| PyCharm  | [jetbrains.com/help/pycharm/connect-to-devcontainer.html](https://www.jetbrains.com/help/pycharm/connect-to-devcontainer.html) |

On first open, the IDE will build the image and start the container. It then runs `pixi run devcontainer-install` automatically, which downloads the pixi environment and all agent CLIs into the named volume. This takes several minutes the first time.

!!! tip

    After changing `devcontainer.json` (e.g. to add extensions), use your IDE's **"Rebuild Container"** command to pick up the changes. This is distinct from `pixi run devcontainer-rebuild`, which only rebuilds the Docker image.

## Terminal / Neovim / Helix

For editors that don't speak the devcontainer spec, a Docker Compose workflow provides equivalent access using pixi tasks. Your editor runs on the host and sees changes immediately via the bind mount — nothing needs to be installed inside the container.

Start the container in the background:

```bash
pixi run devcontainer-start
```

Open a shell inside it:

```bash
pixi run devcontainer-exec
```

On first use, run the setup step inside the container:

```bash
pixi run devcontainer-install
```

This installs the pixi environment, external skills, and all agent CLIs into the named volume. Subsequent starts skip this step — the volume persists between runs.

When you are done:

```bash
pixi run devcontainer-stop
```

## API keys

The sandbox reads API keys from your host shell environment and forwards them into the container. Export whichever keys you need before starting the container:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GEMINI_API_KEY=...
export GOOGLE_API_KEY=...
export OPENAI_API_KEY=sk-...
export OPENROUTER_API_KEY=...
export GITHUB_TOKEN=...
```

Keys are injected at container start time. If you add or rotate a key, restart the container to pick it up.

## Running agents

All agent CLIs are on `PATH` inside the container. Run them from `/workspace`. Because the container is the sandbox, use each agent's fully autonomous / unrestricted mode — there is no need for the agent to ask permission before taking actions.

=== "Claude Code"

    ```bash
    claude --dangerously-skip-permissions
    ```

    The `--dangerously-skip-permissions` flag disables all confirmation prompts and lets Claude act without asking. The alarming name refers to the risk of running this way on an *uncontained* host machine — inside the container it is the intended mode.

=== "Gemini"

    ```bash
    gemini --approval-mode=yolo
    ```

    Use yolo mode to automatically allow all agent actions. Yolo mode can only be used in a trusted workspace.

=== "Codex"

    ```bash
    codex --full-auto
    ```

    The `--full-auto` flag enables fully autonomous operation without confirmation prompts.

=== "Pi"

    ```bash
    pi
    ```

    The Pi agent harness is all YOLO all the time. Not for the faint of heart, but perfectly safe inside the container sandbox.

=== "OpenCode"

    ```bash
    opencode
    ```

    OpenCode doesn't have a YOLO mode. See [GitHub issue 11831](https://github.com/anomalyco/opencode/issues/11831).

## Resetting the environment

If the pixi environment or agent CLIs get into a bad state, reset everything:

```bash
pixi run devcontainer-rebuild
```

This removes the `agent-skills-pixi` Docker volume (destroying the Linux pixi environment and installed agent CLIs) and rebuilds the Docker image from scratch. Your repository files are unaffected — they live on your host via the bind mount and are never stored in the container.
