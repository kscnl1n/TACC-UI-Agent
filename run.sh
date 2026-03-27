
#!/usr/bin/env bash
set -euo pipefail

PROMPT=${1:-"Turn these input files into a website dashboard."}


{
  printf '{"sessionId":"c9d150","runId":"pre-fix-2","hypothesisId":"H1_H2_H3_H4_H5","location":"run.sh:7","message":"Runtime shell context","data":{"pwd":"%s","shell":"%s","path":"%s","bash_version":"%s"},"timestamp":%s}\n' \
    "$PWD" "${SHELL:-unknown}" "${PATH:-unknown}" "${BASH_VERSION:-unknown}" "$(date +%s000)"
  printf '{"sessionId":"c9d150","runId":"pre-fix-2","hypothesisId":"H1_H2","location":"run.sh:10","message":"Python command resolution","data":{"python":"%s","python3":"%s","pip":"%s","pip3":"%s"},"timestamp":%s}\n' \
    "$(command -v python 2>/dev/null || printf 'missing')" \
    "$(command -v python3 2>/dev/null || printf 'missing')" \
    "$(command -v pip 2>/dev/null || printf 'missing')" \
    "$(command -v pip3 2>/dev/null || printf 'missing')" \
    "$(date +%s000)"
} >> debug-c9d150.log


for candidate in python python3 /mnt/c/Python313/python.exe python.exe; do
  if [[ "$candidate" == /* ]]; then
    [[ -x "$candidate" ]] || continue
  else
    command -v "$candidate" >/dev/null 2>&1 || continue
  fi
  if "$candidate" -c "import langchain_core,langchain_ollama,pandas" >/dev/null 2>&1; then
    PYTHON_CMD="$candidate"
    break
  fi
done

printf '{"sessionId":"c9d150","runId":"post-fix-2","hypothesisId":"H1_H2_H3_H5","location":"run.sh:35","message":"Selected python candidate","data":{"python_cmd":"%s"},"timestamp":%s}\n' \
  "${PYTHON_CMD:-missing}" "$(date +%s000)" >> debug-c9d150.log


if [[ -z "$PYTHON_CMD" ]]; then
  printf '{"sessionId":"c9d150","runId":"post-fix-2","hypothesisId":"H1_H2_H3_H5","location":"run.sh:41","message":"No interpreter with required modules found","data":{"hint":"Install with target interpreter using -m pip install -r requirements.txt"},"timestamp":%s}\n' \
    "$(date +%s000)" >> debug-c9d150.log
  echo "No Python interpreter with required modules found. Install deps with the exact interpreter, e.g. /mnt/c/Python313/python.exe -m pip install -r requirements.txt" >&2
  exit 1
fi
"$PYTHON_CMD" - <<'PY' >> debug-c9d150.log 2>&1
import importlib.util, json, site, sys, time
payload = {
  "sessionId": "c9d150",
  "runId": "post-fix-2",
  "hypothesisId": "H1_H2_H3_H5",
  "location": "run.sh:51",
  "message": "Selected interpreter details",
  "data": {
    "executable": sys.executable,
    "version": sys.version.split()[0],
    "site_packages": site.getsitepackages() if hasattr(site, "getsitepackages") else [],
    "has_langchain_core": importlib.util.find_spec("langchain_core") is not None,
    "has_langchain_ollama": importlib.util.find_spec("langchain_ollama") is not None,
    "has_pandas": importlib.util.find_spec("pandas") is not None
  },
  "timestamp": int(time.time() * 1000)
}
print(json.dumps(payload))
PY


"$PYTHON_CMD" agent.py --prompt "$PROMPT"
