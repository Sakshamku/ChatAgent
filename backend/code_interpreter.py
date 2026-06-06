"""
Secure Python Code Interpreter / Execution Sandbox.

Features:
- Isolated subprocess execution with timeout
- Blocked dangerous commands (os.system, subprocess, etc.)
- Captures stdout, stderr, return code
- Matplotlib chart capture and rendering
- DataFrame display support
- File generation and download support
- Per-thread temp workspace management
- Auto-cleanup of old temp files
"""

from __future__ import annotations

import io
import os
import re
import sys
import json
import shutil
import signal
import base64
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================================================
# Configuration
# =========================================================

EXECUTION_TIMEOUT = 30          # seconds
MAX_OUTPUT_LENGTH = 50000       # characters
MAX_MEMORY_MB = 512             # memory limit hint
TEMP_DIR_BASE = os.path.join(tempfile.gettempdir(), "chatagent_workspaces")

# Blocked imports and builtins
BLOCKED_IMPORTS = {
    "os.system", "os.popen", "os.spawn", "os.exec",
    "subprocess", "shutil.rmtree", "shutil.move",
    "signal", "ctypes", "multiprocessing",
    "socket", "http", "urllib", "requests",
    "telnetlib", "ftplib", "smtplib",
    "webbrowser", "antigravity",
}

BLOCKED_BUILTINS = {
    "exec", "eval", "compile", "__import__",
    "breakpoint", "exit", "quit",
}

BLOCKED_PATTERNS = [
    r"os\.system\s*\(",
    r"os\.popen\s*\(",
    r"subprocess\.\w+\s*\(",
    r"shutil\.rmtree\s*\(",
    r"__import__\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
    r"compile\s*\(",
    r"open\s*\([^)]*['\"]w['\"]",   # block write-mode open (except via allowed pattern)
    r"socket\s*\(",
    r"http\.client",
    r"urllib\.request",
    r"requests\.\w+",
    r"webbrowser",
    r"os\.remove\s*\(",
    r"os\.unlink\s*\(",
    r"os\.rename\s*\(",
    r"os\.kill\s*\(",
    r"signal\.\w+",
]

ALLOWED_WRITE_PATTERNS = [
    r"open\s*\([^)]*workspace",     # allow writing to workspace dir
    r"to_csv\s*\(",                 # pandas to_csv
    r"to_excel\s*\(",              # pandas to_excel
    r"savefig\s*\(",               # matplotlib savefig
    r"to_json\s*\(",               # pandas to_json
]

# Allowed data science libraries
ALLOWED_LIBRARIES = {
    "pandas", "numpy", "matplotlib", "plotly", "seaborn",
    "scipy", "sklearn", "statistics", "math", "random",
    "collections", "itertools", "functools", "datetime",
    "json", "csv", "re", "string", "textwrap",
    "typing", "dataclasses", "enum", "pathlib",
    "io", "base64", "hashlib", "copy", "decimal",
    "fractions", "pprint", "operator", "abc",
    "openpyxl", "xlrd", "pdfplumber",
}

# =========================================================
# Workspace Management
# =========================================================

def get_workspace_dir(thread_id: str) -> str:
    """Get or create a per-thread workspace directory."""
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(thread_id))
    workspace = os.path.join(TEMP_DIR_BASE, safe_id)
    os.makedirs(workspace, exist_ok=True)
    return workspace


def save_uploaded_file(thread_id: str, filename: str, file_bytes: bytes) -> str:
    """Save an uploaded file to the thread's workspace and return the path."""
    workspace = get_workspace_dir(thread_id)
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    filepath = os.path.join(workspace, safe_name)
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    return filepath


def cleanup_old_workspaces(max_age_hours: int = 24):
    """Remove workspaces older than max_age_hours."""
    if not os.path.exists(TEMP_DIR_BASE):
        return
    import time
    now = time.time()
    for name in os.listdir(TEMP_DIR_BASE):
        path = os.path.join(TEMP_DIR_BASE, name)
        if os.path.isdir(path):
            try:
                age_hours = (now - os.path.getmtime(path)) / 3600
                if age_hours > max_age_hours:
                    shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass


def list_workspace_files(thread_id: str) -> List[str]:
    """List files in the thread's workspace."""
    workspace = get_workspace_dir(thread_id)
    if not os.path.exists(workspace):
        return []
    return [f for f in os.listdir(workspace) if os.path.isfile(os.path.join(workspace, f))]


def get_workspace_file_path(thread_id: str, filename: str) -> Optional[str]:
    """Get full path for a workspace file, or None if not found."""
    workspace = get_workspace_dir(thread_id)
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    filepath = os.path.join(workspace, safe_name)
    if os.path.exists(filepath):
        return filepath
    return None

# =========================================================
# Code Validation / Security
# =========================================================

def validate_code(code: str) -> Tuple[bool, str]:
    """
    Validate Python code for security.
    Returns (is_safe, reason).
    """
    if not code or not code.strip():
        return False, "Empty code"

    # Check for blocked patterns
    for pattern in BLOCKED_PATTERNS:
        # Skip patterns that are allowed via write patterns
        is_allowed = False
        for allow_pattern in ALLOWED_WRITE_PATTERNS:
            if re.search(allow_pattern, code):
                is_allowed = True
                break
        
        # Special handling for open() with write mode
        if "open\\s*\\(" in pattern and is_allowed:
            continue
            
        if re.search(pattern, code):
            return False, f"Blocked pattern detected: {pattern}"

    # Check import statements
    for line in code.split('\n'):
        line = line.strip()
        if line.startswith('import ') or line.startswith('from '):
            # Extract module name
            if line.startswith('import '):
                module = line.replace('import ', '').split('as')[0].split(',')[0].strip()
            else:
                module = line.replace('from ', '').split(' import')[0].strip()
            
            # Get top-level module
            top_module = module.split('.')[0]
            
            # Check if blocked
            for blocked in BLOCKED_IMPORTS:
                if blocked in line:
                    return False, f"Blocked import: {blocked}"
            
            # Check if not in allowed list (if we're restricting)
            # We allow all imports but block the dangerous ones above
            if top_module in ("subprocess", "socket", "http", "urllib", "requests",
                              "webbrowser", "telnetlib", "ftplib", "smtplib",
                              "ctypes", "multiprocessing"):
                return False, f"Blocked module: {top_module}"

    return True, "OK"


def prepare_code(code: str, thread_id: str) -> str:
    """
    Wrap user code with:
    - Matplotlib backend setup
    - Workspace path injection
    - Output capture helpers
    - DataFrame display helper
    """
    workspace = get_workspace_dir(thread_id)
    workspace_escaped = workspace.replace('\\', '\\\\')
    
    wrapper = f'''
import sys as _sys
import io as _io
import os as _os
import json as _json
import base64 as _base64
import traceback as _traceback

# Matplotlib setup - use Agg backend and capture figures
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as _plt
except ImportError:
    _plt = None

# Workspace setup
WORKSPACE = r"{workspace_escaped}"
_os.chdir(WORKSPACE)
_sys.path.insert(0, WORKSPACE)

# DataFrame display helper
try:
    import pandas as _pd
    def _display_dataframe(df, max_rows=50):
        """Convert DataFrame to dict for JSON serialization."""
        if isinstance(df, _pd.DataFrame):
            return {{
                "type": "dataframe",
                "columns": df.columns.tolist(),
                "data": df.head(max_rows).values.tolist(),
                "dtypes": [str(dt) for dt in df.dtypes],
                "shape": list(df.shape),
                "index": df.index.tolist()[:max_rows]
            }}
        return None
except ImportError:
    _pd = None
    def _display_dataframe(df, max_rows=50):
        return None

# Chart capture helper
def _capture_plots():
    """Capture all matplotlib figures as base64 images."""
    charts = []
    if _plt is not None:
        for fig_num in _plt.get_fignums():
            fig = _plt.figure(fig_num)
            buf = _io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            img_b64 = _base64.b64encode(buf.read()).decode('utf-8')
            charts.append({{
                "type": "chart",
                "format": "png",
                "base64": img_b64
            }})
            buf.close()
        _plt.close('all')
    return charts

# File scan helper
def _scan_workspace_files():
    """List generated files in workspace."""
    files = []
    for fname in _os.listdir(WORKSPACE):
        fpath = _os.path.join(WORKSPACE, fname)
        if _os.path.isfile(fpath):
            fsize = _os.path.getsize(fpath)
            files.append({{"name": fname, "size": fsize, "path": fpath}})
    return files

# Capture stdout/stderr
_old_stdout = _sys.stdout
_old_stderr = _sys.stderr
_captured_stdout = _io.StringIO()
_captured_stderr = _io.StringIO()
_sys.stdout = _captured_stdout
_sys.stderr = _captured_stderr

_result_objects = []

try:
# ---- USER CODE START ----
{code}
# ---- USER CODE END ----

except Exception as e:
    _traceback.print_exc(file=_captured_stderr)

finally:
    _sys.stdout = _old_stdout
    _sys.stderr = _old_stderr

# Collect results
_output = {{
    "stdout": _captured_stdout.getvalue(),
    "stderr": _captured_stderr.getvalue(),
    "charts": _capture_plots(),
    "files": _scan_workspace_files(),
    "result_objects": _result_objects,
}}

# Print as JSON marker for parsing
print("<<<EXECUTION_RESULT>>>")
print(_json.dumps(_output, default=str))
'''
    return wrapper

# =========================================================
# Code Execution Engine
# =========================================================

def execute_python(
    code: str,
    thread_id: str,
    timeout: int = EXECUTION_TIMEOUT,
) -> Dict[str, Any]:
    """
    Execute Python code in a secure subprocess.
    
    Args:
        code: Python code to execute
        thread_id: Thread ID for workspace isolation
        timeout: Execution timeout in seconds
    
    Returns:
        Dict with keys: success, stdout, stderr, charts, files, error, execution_time
    """
    # Validate code first
    is_safe, reason = validate_code(code)
    if not is_safe:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Code validation failed: {reason}",
            "charts": [],
            "files": [],
            "error": reason,
            "execution_time": 0,
        }
    
    # Prepare wrapped code
    wrapped_code = prepare_code(code, thread_id)
    
    # Write to temp file for subprocess execution
    workspace = get_workspace_dir(thread_id)
    code_file = os.path.join(workspace, "_exec_code.py")
    
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(wrapped_code)
    
    # Execute in subprocess
    import subprocess
    import time
    
    start_time = time.time()
    result_data = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "charts": [],
        "files": [],
        "error": None,
        "execution_time": 0,
    }
    
    try:
        proc = subprocess.run(
            [sys.executable, code_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workspace,
            env={
                **{k: v for k, v in os.environ.items() 
                   if k not in ("MISTRAL_API_KEY", "ALPHA_VANTAGE_API_KEY")},
                "PYTHONPATH": workspace,
                "MPLBACKEND": "Agg",
            },
        )
        
        elapsed = time.time() - start_time
        result_data["execution_time"] = round(elapsed, 3)
        
        # Parse output
        full_output = proc.stdout or ""
        full_stderr = proc.stderr or ""
        
        # Extract JSON result from marker
        marker = "<<<EXECUTION_RESULT>>>"
        if marker in full_output:
            parts = full_output.split(marker, 1)
            result_data["stdout"] = parts[0].strip()
            
            try:
                exec_result = json.loads(parts[1].strip())
                result_data["stdout"] = exec_result.get("stdout", result_data["stdout"])
                result_data["stderr"] = exec_result.get("stderr", "") + "\n" + full_stderr
                result_data["charts"] = exec_result.get("charts", [])
                result_data["files"] = exec_result.get("files", [])
                result_data["success"] = True
            except json.JSONDecodeError as e:
                result_data["stderr"] += f"\nFailed to parse execution result: {e}"
                result_data["success"] = proc.returncode == 0
        else:
            result_data["stdout"] = full_output
            result_data["stderr"] = full_stderr
            result_data["success"] = proc.returncode == 0
        
        if proc.returncode != 0 and not result_data["stderr"]:
            result_data["error"] = f"Process exited with code {proc.returncode}"
        
        # Truncate long outputs
        if len(result_data["stdout"]) > MAX_OUTPUT_LENGTH:
            result_data["stdout"] = result_data["stdout"][:MAX_OUTPUT_LENGTH] + "\n... (output truncated)"
        if len(result_data["stderr"]) > MAX_OUTPUT_LENGTH:
            result_data["stderr"] = result_data["stderr"][:MAX_OUTPUT_LENGTH] + "\n... (error truncated)"
    
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        result_data["execution_time"] = round(elapsed, 3)
        result_data["error"] = f"Execution timed out after {timeout} seconds"
        result_data["stderr"] = "Timeout: code took too long to execute"
    
    except Exception as e:
        elapsed = time.time() - start_time
        result_data["execution_time"] = round(elapsed, 3)
        result_data["error"] = str(e)
        result_data["stderr"] = traceback.format_exc()
    
    finally:
        # Clean up code file
        try:
            os.remove(code_file)
        except Exception:
            pass
    
    return result_data


def format_execution_result(result: Dict[str, Any]) -> str:
    """
    Format execution result into a readable string for the AI.
    """
    parts = []
    
    if result.get("stdout"):
        parts.append(f"Output:\n{result['stdout']}")
    
    if result.get("stderr"):
        parts.append(f"Errors:\n{result['stderr']}")
    
    if result.get("charts"):
        parts.append(f"Charts generated: {len(result['charts'])} figure(s)")
    
    if result.get("files"):
        file_names = [f["name"] for f in result["files"]]
        parts.append(f"Files generated: {', '.join(file_names)}")
    
    if result.get("execution_time"):
        parts.append(f"Execution time: {result['execution_time']}s")
    
    if result.get("error"):
        parts.append(f"Error: {result['error']}")
    
    if not parts:
        parts.append("Code executed successfully with no output.")
    
    return "\n\n".join(parts)

# =========================================================
# Cleanup on module load
# =========================================================

# Clean old workspaces on import
try:
    cleanup_old_workspaces(max_age_hours=24)
except Exception:
    pass
