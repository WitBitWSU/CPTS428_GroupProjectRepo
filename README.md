## Input Sanitization Module (`sanitization.py`)

`sanitization.py` implements input sanitization and instruction-data isolation for untrusted email records, HTML bodies, and attachment metadata prior to passing records into `EmailTools` and the LLM.

### 1. Dependencies

Install `beautifulsoup4` (added to `requirements.txt`):

```powershell
python -m pip install beautifulsoup4>=4.12
```

### 2. What It Sanitizes

* **Hidden HTML & Attributes (`strip_hidden_html`)**: Parses `body_html` with BeautifulSoup, strips HTML comments, `<script>`/`<style>` tags, CSS-hidden elements (`display:none`, `visibility:hidden`, zero-size, transparent/white text), and non-rendered attributes (such as `<img alt="...">`).
* **Unicode & Obfuscation (`normalize_text`)**: Applies NFKC Unicode normalization and removes zero-width/directional override characters.
* **Attachment Filenames & Metadata (`sanitize_attachment`, `sanitize_filename`)**: Strips prompt-injection text from attachment filenames while preserving valid extensions, and isolates RTF `metadata` fields inside `<untrusted_attachment_meta>` tags.
* **Instruction-Data Delimiting (`wrap_untrusted`)**: Escapes angle brackets (`<`, `>`) to prevent tag breakout and wraps untrusted fields (`sender`, `subject`, `body`, `body_html`, attachment `body_text`) inside `<untrusted_email_data>` delimiters.
* **System Prompt Hardening (`SANITIZED_SYSTEM_PROMPT`)**: Instructs the agent to treat `<untrusted_email_data>`, `<untrusted_attachment_meta>`, and attached PNG images strictly as passive data and reject forwarding/CC requests to external or neutral-looking addresses not specified in `user_task`.

### 3. Integration into `environment.py`

In `environment.py`, import the sanitizer and hardened prompt at the top of the file:

```python
from sanitization import SANITIZED_SYSTEM_PROMPT, sanitize_mailbox
```

Update `SYSTEM_PROMPTS["hardened"]` to use `SANITIZED_SYSTEM_PROMPT`, and apply `sanitize_mailbox` inside `build_agent_runner` when `agent_mode == "hardened"` (leaving `baseline` untouched):

```python
if agent_mode == "hardened":
    records = sanitize_mailbox(records)
```

### 4. Standalone Verification

You can test `sanitization.py` directly on any fixture without calling an LLM API:

```python
import json
from pathlib import Path
from sanitization import sanitize_mailbox

fixture = json.loads(Path("attacks/exfil_hidden_html.json").read_text(encoding="utf-8"))
clean_emails = sanitize_mailbox(fixture["emails"])
print(json.dumps(clean_emails, indent=2))
```

### 5. Running the Harness with Sanitization Enabled

Run the controls and attack suite using `--agent-mode hardened` (default):

```powershell
python harness.py --all-controls --openai-model <MODEL_ID> --agent-mode hardened --repeats 20
python harness.py --all-attacks --openai-model <MODEL_ID> --agent-mode hardened --repeats 20
```
