FROM ghcr.io/prefix-dev/pixi:0.68.0

# The pixi base image (Ubuntu) ships a user named "ubuntu" at UID/GID 1000.
# We reuse it directly, adding passwordless sudo so the user can install
# additional tooling inside the running container without rebuilding the image.
#
# The repository is NOT copied here. It is bind-mounted from the host at
# container start time via the workspaceMount in devcontainer.json.
# The pixi environment (.pixi/) lives in a separate named Docker volume so
# that Linux and macOS environments never overwrite each other.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends sudo git openssh-client bubblewrap socat \
    && rm -rf /var/lib/apt/lists/* \
    && echo "ubuntu ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu \
    && chmod u+s /usr/bin/bwrap \
    && mkdir -p /workspace/.pixi \
    && chown ubuntu:ubuntu /workspace/.pixi

USER ubuntu
# Activate the pixi environment in every interactive shell.
# shell-hook is guarded so it fails silently before devcontainer-install has run.
# hadolint ignore=SC2016
RUN echo 'eval "$(pixi shell-hook --shell bash 2>/dev/null || true)"' >> ~/.bashrc
WORKDIR /workspace
