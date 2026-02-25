"""Streamlit UI for ReMD."""

from __future__ import annotations

import os
import re
import signal

import streamlit as st
from streamlit.components.v1 import html as st_html

from ReMD.file_filter import (
    compile_patterns,
    matches_any_pattern,
    parse_pattern_input,
    validate_patterns,
)
from ReMD.markdown_renderer import render_markdown
from ReMD.models import ProviderType
from ReMD.providers.azure_devops import AzureDevOpsError, AzureDevOpsProvider
from ReMD.providers.github import GitHubError, GitHubProvider, RateLimitError
from ReMD.url_parser import URLParseError, parse_repo_url
from ReMD import token_store


def _qp(key: str, default: str = "") -> str:
    """Read a query parameter, returning *default* if absent."""
    params = st.query_params
    return params.get(key, default)


def main() -> None:
    st.set_page_config(
        page_title="ReMD",
        page_icon="📄",
        layout="wide",
    )

    # Hide Streamlit's default toolbar (Deploy, Stop, etc.)
    st.markdown(
        "<style>[data-testid='stToolbar'] { display: none; }</style>",
        unsafe_allow_html=True,
    )

    # --- Header with settings popover ---
    header_left, header_right = st.columns([8, 1])
    with header_left:
        st.title("ReMD")
    with header_right:
        st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)
        with st.popover("", use_container_width=True):
            st.subheader("Settings")

            saved_gh = token_store.load("github_token") or ""
            github_token = st.text_input(
                "GitHub Token (optional)",
                value=_qp("token") or saved_gh,
                type="password",
                help="Required for private repos. Increases rate limit from 60 to 5,000 requests/hour.",
            )

            saved_azdo = token_store.load("azdo_pat") or ""
            azdo_pat = st.text_input(
                "Azure DevOps PAT (optional)",
                value=_qp("pat") or saved_azdo,
                type="password",
                help="Required for private Azure DevOps repositories.",
            )

            if token_store.is_available():
                remember = st.checkbox(
                    "Save tokens to OS keychain",
                    value=bool(saved_gh or saved_azdo),
                    help="Tokens are stored securely in macOS Keychain or Windows Credential Manager.",
                )
                if remember:
                    if github_token:
                        token_store.save("github_token", github_token)
                    elif saved_gh:
                        token_store.delete("github_token")
                    if azdo_pat:
                        token_store.save("azdo_pat", azdo_pat)
                    elif saved_azdo:
                        token_store.delete("azdo_pat")
                else:
                    # Checkbox unchecked — clear any saved tokens
                    if saved_gh:
                        token_store.delete("github_token")
                    if saved_azdo:
                        token_store.delete("azdo_pat")

            default_size = float(_qp("max_size", "1.0"))
            max_file_size_mb = st.number_input(
                "Max file size (MB)",
                min_value=0.1,
                max_value=100.0,
                value=min(max(default_size, 0.1), 100.0),
                step=0.5,
                help="Files larger than this will be skipped. Set to 0 to include all.",
            )
            max_file_size = int(max_file_size_mb * 1_000_000)

    st.caption(
        "Convert a GitHub / Azure DevOps repository into a single Markdown file."
    )

    # --- Main area ---
    url = st.text_input(
        "Repository URL",
        value=_qp("url"),
        placeholder="https://github.com/owner/repo",
    )

    # --- Regex filter ---
    filter_raw = st.text_input(
        "File filter (regex, comma-separated)",
        value=_qp("filter"),
        placeholder=r"\.py$, \.ts$, src/.*\.js$",
        help=(
            "Only files whose path matches at least one pattern will be included. "
            "Separate multiple patterns with commas. Leave empty to include all files."
        ),
    )

    # Validate patterns in real-time
    filter_patterns = parse_pattern_input(filter_raw)
    filter_errors = validate_patterns(filter_patterns) if filter_patterns else []
    has_filter_error = bool(filter_errors)

    if has_filter_error:
        # Red border via custom CSS + error messages
        st.markdown(
            """<style>
            div[data-testid="stTextInput"]:has(input[aria-label="File filter (regex, comma-separated)"]) input {
                border-color: #ff4b4b !important;
                box-shadow: 0 0 0 1px #ff4b4b !important;
            }
            </style>""",
            unsafe_allow_html=True,
        )
        for err in filter_errors:
            st.error(f"Invalid regex: {err}")

    convert_clicked = st.button(
        "Convert",
        type="primary",
        use_container_width=True,
        disabled=has_filter_error,
    )

    if convert_clicked and url:
        compiled = compile_patterns(filter_patterns)
        _run_conversion(url, github_token, azdo_pat, max_file_size, compiled)
    elif convert_clicked:
        st.error("Please enter a repository URL.")

    # Show previous result after rerun (e.g. download button click)
    if not convert_clicked and "result" in st.session_state:
        _show_result(st.session_state["result"])

    # --- Heartbeat: shut down when the browser tab closes ---
    _inject_shutdown_heartbeat()


def _show_result(result: dict) -> None:
    """Display download button and preview from a stored result."""
    markdown_output = result["markdown"]
    filename = result["filename"]
    errors = result["errors"]

    if errors:
        with st.expander(f"⚠ {len(errors)} errors", expanded=False):
            for err in errors:
                st.text(err)

    st.download_button(
        label="Download Markdown",
        data=markdown_output,
        file_name=filename,
        mime="text/markdown",
        use_container_width=True,
    )

    _PREVIEW_MAX_LINES = 1000
    preview_lines = markdown_output.split("\n")
    with st.expander("Preview", expanded=True):
        if len(preview_lines) > _PREVIEW_MAX_LINES:
            truncated = "\n".join(preview_lines[:_PREVIEW_MAX_LINES])
            st.code(truncated, language="markdown")
            st.caption(
                f"Preview is truncated to {_PREVIEW_MAX_LINES:,} lines "
                f"(total {len(preview_lines):,} lines). "
                "Download the file for the full content."
            )
        else:
            st.code(markdown_output, language="markdown")


def _run_conversion(
    url: str,
    github_token: str,
    azdo_pat: str,
    max_file_size: int,
    path_patterns: list[re.Pattern[str]] | None = None,
) -> None:
    # Parse URL
    try:
        repo_info = parse_repo_url(url)
    except URLParseError as exc:
        st.error(f"Invalid URL: {exc}")
        return

    # Select provider (strip tokens to avoid whitespace from copy-paste)
    gh_token = github_token.strip() or None
    azdo_token = azdo_pat.strip() or None
    if repo_info.provider == ProviderType.GITHUB:
        provider = GitHubProvider(token=gh_token, api_host=repo_info.api_host)
    else:
        provider = AzureDevOpsProvider(pat=azdo_token)

    repo_display = f"{repo_info.owner}/{repo_info.repo}"

    try:
        # List files
        with st.spinner("Fetching file list..."):
            files = provider.list_files(repo_info)

        if not files:
            st.warning("No files found in the repository.")
            return

        # Apply regex path filter
        if path_patterns:
            before = len(files)
            files = [
                f for f in files if matches_any_pattern(f.path, path_patterns)
            ]
            filtered_out = before - len(files)
        else:
            filtered_out = 0

        if not files:
            st.warning("No files matched the filter patterns.")
            return

        text_files = [f for f in files if not f.is_binary]
        msg = (
            f"Found {len(files)} files ({len(text_files)} text, "
            f"{len(files) - len(text_files)} binary/skipped)"
        )
        if filtered_out:
            msg += f" — {filtered_out} files excluded by filter"
        st.info(msg + ".")

        # Fetch file contents with progress
        progress_bar = st.progress(0, text="Fetching files...")
        status_text = st.empty()

        for progress in provider.fetch_all_files(repo_info, files, max_file_size):
            pct = progress.fetched_files / max(progress.total_files, 1)
            progress_bar.progress(pct, text=f"Fetching: {progress.current_file}")
            status_text.text(
                f"{progress.fetched_files}/{progress.total_files} files processed"
            )

        progress_bar.progress(1.0, text="Done!")

        # Render Markdown
        markdown_output = render_markdown(repo_display, files)
        filename = f"{repo_info.owner}_{repo_info.repo}.md"

        # Save result to session state so it survives reruns
        st.session_state["result"] = {
            "markdown": markdown_output,
            "filename": filename,
            "errors": progress.errors,
        }

        _show_result(st.session_state["result"])

    except RateLimitError as exc:
        st.error(str(exc))
        st.info(
            "Tip: Add a GitHub token in Settings (⋮) to increase your rate limit "
            "from 60 to 5,000 requests per hour."
        )
    except (GitHubError, AzureDevOpsError) as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")


def _inject_shutdown_heartbeat() -> None:
    """Inject a JS heartbeat that kills the server when the browser tab closes.

    The browser sends a /healthz ping every 3 s via ``setInterval``.
    When the tab is closed (``beforeunload``), a final ``/_shutdown`` beacon
    is sent. On the server side a ``tornado.web.RequestHandler`` listens on
    ``/_shutdown`` and terminates the process.

    As a fallback the server also tracks heartbeat timestamps — if no ping
    arrives for 10 s it self-terminates via a watchdog thread.
    """
    _register_shutdown_route()

    st_html(
        """
        <script>
        // Heartbeat ping
        setInterval(() => {
            fetch("/_heartbeat").catch(() => {});
        }, 3000);

        // Shutdown on tab close / navigate away
        window.addEventListener("beforeunload", () => {
            navigator.sendBeacon("/_shutdown");
        });
        </script>
        """,
        height=0,
    )


_SHUTDOWN_REGISTERED = False


def _register_shutdown_route() -> None:
    """Register /_shutdown and /_heartbeat on the running Tornado server (once)."""
    global _SHUTDOWN_REGISTERED
    if _SHUTDOWN_REGISTERED:
        return
    _SHUTDOWN_REGISTERED = True

    import threading
    import time

    import tornado.web
    from streamlit.runtime.runtime import Runtime

    last_heartbeat = time.time()

    class HeartbeatHandler(tornado.web.RequestHandler):
        def get(self):
            nonlocal last_heartbeat
            last_heartbeat = time.time()
            self.set_status(200)
            self.finish("ok")

    class ShutdownHandler(tornado.web.RequestHandler):
        def post(self):
            self.set_status(200)
            self.finish("bye")
            _kill()

        def get(self):
            self.post()

    def _kill() -> None:
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)

    def _watchdog() -> None:
        """Kill the process if no heartbeat for 10 seconds after the first one."""
        # Wait for the first heartbeat to arrive (browser loaded)
        while time.time() - last_heartbeat < 1:
            time.sleep(3)
        # Now watch for staleness
        while True:
            time.sleep(5)
            if time.time() - last_heartbeat > 10:
                _kill()
                return

    try:
        runtime = Runtime.instance()
        server = None
        # Access the Tornado app via the runtime's server
        if hasattr(runtime, "_server") and runtime._server is not None:
            server = runtime._server
        if server is None:
            # Fallback: try accessing via the newer attribute
            for attr in ("_server", "server"):
                server = getattr(runtime, attr, None)
                if server is not None:
                    break

        if server is not None:
            app = None
            for attr in ("_app", "app"):
                app = getattr(server, attr, None)
                if app is not None:
                    break
            if app is None and hasattr(server, "_tornado_server"):
                tornado_server = server._tornado_server
                if hasattr(tornado_server, "request_callback"):
                    app = tornado_server.request_callback
            if app is not None and hasattr(app, "wildcard_router"):
                app.wildcard_router.add_rules([
                    (r"/_heartbeat", HeartbeatHandler),
                    (r"/_shutdown", ShutdownHandler),
                ])
                threading.Thread(target=_watchdog, daemon=True).start()
    except Exception:
        # If we cannot register routes, the server still works —
        # the user just needs to close the console window manually.
        pass


if __name__ == "__main__":
    main()
