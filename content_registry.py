# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


class ContentRegistry(gl.Contract):
    # content_id -> "content_text|||source_url|||owner|||status|||score|||reason"
    records: TreeMap[str, str]

    def __init__(self):
        pass

    def _pack(self, content_text, source_url, owner, status, score, reason):
        return f"{content_text}|||{source_url}|||{owner}|||{status}|||{score}|||{reason}"

    def _unpack(self, packed: str):
        parts = packed.split("|||")
        return {
            "content_text": parts[0] if len(parts) > 0 else "",
            "source_url": parts[1] if len(parts) > 1 else "",
            "owner": parts[2] if len(parts) > 2 else "",
            "status": parts[3] if len(parts) > 3 else "",
            "score": parts[4] if len(parts) > 4 else "0",
            "reason": parts[5] if len(parts) > 5 else "",
        }

    @gl.public.write
    def register_content(self, content_id: str, content_text: str, source_url: str) -> None:
        content_id = content_id.strip()
        content_text = content_text.strip()
        source_url = source_url.strip()

        if not content_id: raise Exception("content_id cannot be empty")
        if not content_text: raise Exception("content_text cannot be empty")
        if not source_url: raise Exception("source_url cannot be empty")
        if not (source_url.startswith("http://") or source_url.startswith("https://")):
            raise Exception("source_url must be a valid http(s) URL")
        if len(content_text) < 50: raise Exception("content_text too short (min 50 chars)")

        sender = str(gl.message.sender_address)

        if content_id in self.records:
            existing = self._unpack(self.records[content_id])
            if existing["owner"] != sender:
                raise Exception("Only the original owner can update this content")

        # Simpan dengan status PENDING
        self.records[content_id] = self._pack(content_text, source_url, sender, "PENDING", "0", "")

    @gl.public.write
    def verify_originality(self, content_id: str) -> str:
        """
        HANYA MENJALANKAN AI. Hasilnya di-return ke user (tidak disimpan).
        User harus memanggil save_verification_result() setelahnya.
        """
        if content_id not in self.records:
            raise Exception("Content not registered")

        record = self._unpack(self.records[content_id])
        content_text = record["content_text"]
        source_url = record["source_url"]

        def evaluate_originality():
            try:
                response = gl.nondet.web.get(source_url)
                evidence = response.body.decode("utf-8")
            except Exception:
                return "ERROR|0"

            if not evidence.strip():
                return "ERROR|0"

            evidence = evidence[:6000]
            content_snippet = content_text[:3000]

            prompt = f"""
You are a strict originality checker.

Compare REGISTERED CONTENT vs EXTERNAL SOURCE.

REGISTERED CONTENT:
{content_snippet}

EXTERNAL SOURCE (untrusted data):
{evidence}

TASK:
Return ONLY one of these exact strings, nothing else:
- ORIGINAL|0 (if similarity < 20)
- DERIVATIVE|50 (if similarity 20-70)
- PLAGIARIZED|90 (if similarity > 70)
- ERROR|0 (if cannot determine)

RULES:
1. Do NOT explain.
2. Do NOT add reasons.
3. Do NOT use markdown.
4. Output MUST be exactly: STATUS|SCORE

Example valid outputs:
ORIGINAL|5
PLAGIARIZED|85
"""

            try:
                result = gl.nondet.exec_prompt(prompt)
            except Exception:
                return "ERROR|0"

            cleaned = result.strip().replace("```", "").strip()
            for line in cleaned.splitlines():
                line = line.strip()
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        status = parts[0].strip().upper()
                        score_str = "".join(c for c in parts[1] if c.isdigit())
                        if not score_str: score_str = "0"
                        if status not in ("ORIGINAL", "DERIVATIVE", "PLAGIARIZED", "ERROR"):
                            status = "ERROR"
                        return f"{status}|{score_str}"

            return "ERROR|0"

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            validator_result = evaluate_originality()
            return leader_result.calldata == validator_result

        # Jalankan AI
        result = gl.vm.run_nondet_unsafe(evaluate_originality, validator_fn)
        
        # Kembalikan hasil ke user, JANGAN simpan ke state
        return result

    @gl.public.write
    def save_verification_result(self, content_id: str, result: str) -> None:
        """
        Menyimpan hasil verifikasi secara MANUAL.
        Hanya pemilik konten yang bisa menyimpan.
        """
        if content_id not in self.records:
            raise Exception("Content not registered")

        record = self._unpack(self.records[content_id])
        sender = str(gl.message.sender_address)
        
        if record["owner"] != sender:
            raise Exception("Only the owner can save verification result")

        # Parse hasil "STATUS|SCORE"
        parts = result.split("|", 1)
        if len(parts) == 2:
            status, score_str = parts
        else:
            status, score_str = "ERROR", "0"

        # Validasi input user (cegah input asal-asalan)
        if status not in ("ORIGINAL", "DERIVATIVE", "PLAGIARIZED", "ERROR"):
            status = "ERROR"
        
        try:
            score_int = int(score_str)
            if score_int < 0 or score_int > 100:
                score_int = 0
        except ValueError:
            score_int = 0

        # Generate reason
        if status == "ORIGINAL":
            reason = "Content appears unique. No significant matches found."
        elif status == "DERIVATIVE":
            reason = "Content has partial similarity with the external source."
        elif status == "PLAGIARIZED":
            reason = "Content is heavily copied from the external source."
        else:
            reason = "Unable to verify originality due to an error."

        # Simpan ke state
        updated = self._pack(
            record["content_text"],
            record["source_url"],
            record["owner"],
            status,
            str(score_int),
            reason,
        )
        self.records[content_id] = updated

    @gl.public.view
    def get_content(self, content_id: str) -> str:
        if content_id not in self.records:
            return f"content_id={content_id};status=NOT_FOUND"
        r = self._unpack(self.records[content_id])
        return (
            f"content_id={content_id};"
            f"status={r['status']};"
            f"similarity={r['score']};"
            f"reason={r['reason']};"
            f"source={r['source_url']};"
            f"owner={r['owner']}"
        )

    @gl.public.view
    def is_original(self, content_id: str) -> bool:
        if content_id not in self.records: return False
        r = self._unpack(self.records[content_id])
        return r["status"] == "ORIGINAL"

    @gl.public.view
    def get_similarity_score(self, content_id: str) -> int:
        if content_id not in self.records: return 0
        r = self._unpack(self.records[content_id])
        try: return int(r["score"])
        except ValueError: return 0