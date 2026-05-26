"""integrity_seal.py — IntegrityContract: proof_trace_hash للشهادات.

⚠️  هذا ليس بديلًا عن old_nand. هذا تصميم مُختلف جذريًّا.

الفرق المبدئيّ:

   old_nand               proof_trace_hash
   ────────               ────────────────
   مصدر معلومة            خَتْم على شهادة
   مُتنكِّر كـ"إحداثيّة"  مُعلَن كـ"ختم سلامة"
   يَدّعي تَحديد سياق     يُؤمِّن أنّ الوثيقة لم تُعَدَّل
   مدخله: حقول semantic   مدخله: claims + trace (الشكل القانوني)
   مكانه: بَجانب التحليل  مكانه: قسم integrity{} مُنفصل

القاعدة الذهبيّة (مَكتوبة كاختبار assertion):

   ❌ ممنوع:  claim.source == "hash"
   ❌ ممنوع:  hash يَدخل في فضاء المعنى
   ✓ مَسموح: integrity.proof_trace_hash يَختِم claims + trace

البنية المُعتمَدة (مُطابقة لِما اقترَحه المستخدم):

   ProofRecord:
     input: <الكلمة>
     status: Certificate | Hypothesis | Zero
     closure: CLOSED | OPEN
     claims:                          ← الادّعاءات اللغوية
       - id: <اسم الادّعاء>
         value: <قيمة>
         source: <اسم العقد المُصدِر>
     trace:                           ← مسار العقود التي اشتغلت
       - contract: <اسم العقد>
         result: PASS | FAIL | <ملاحظة>
     residuals: [...]
     blockers: [...]
     integrity:                       ← الختم — وَحده هنا
       canonicalization: "json-canonical-v1"
       hash_algorithm: "sha256"
       proof_trace_hash: "sha256:..."
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any


# ============================================================================
# Canonical JSON serialization
# ============================================================================

def canonical_json(obj: Any) -> str:
    """Serialize to canonical JSON for hashing.

    Canonical = deterministic = sorted keys, no whitespace, UTF-8.
    Two structurally-equal inputs produce byte-equal output.
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


# ============================================================================
# IntegrityContract — the only place where hashes happen
# ============================================================================

CANONICALIZATION_VERSION = "json-canonical-v1"
HASH_ALGORITHM = "sha256"


@dataclass
class Integrity:
    """The sealed section. Lives AT THE END of a ProofRecord, separate
    from claims. It is NOT a source-of-claim — it is a tamper seal."""
    canonicalization: str = CANONICALIZATION_VERSION
    hash_algorithm: str = HASH_ALGORITHM
    proof_trace_hash: str = ""


def compute_proof_trace_hash(claims: list, trace: list) -> str:
    """The ONLY hash function in the integrity layer.

    Input: claims + trace, in their structured form.
    Output: 'sha256:<hex>' — a sealed fingerprint.

    THIS FUNCTION MUST NEVER BE CALLED FROM A CLAIM'S source FIELD.
    The hash seals; it does not explain.
    """
    payload = {"claims": claims, "trace": trace}
    body = canonical_json(payload).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    return f"{HASH_ALGORITHM}:{digest}"


def seal(claims: list, trace: list) -> Integrity:
    """Construct the Integrity seal for a ProofRecord."""
    return Integrity(
        canonicalization=CANONICALIZATION_VERSION,
        hash_algorithm=HASH_ALGORITHM,
        proof_trace_hash=compute_proof_trace_hash(claims, trace),
    )


# ============================================================================
# Constitutional check — the rule must be enforceable, not just promised
# ============================================================================

def assert_hash_not_source_of_claim(record: dict) -> None:
    """Raise AssertionError if any claim cites a hash as its source.

    This is the constitutional check the user defined:

        hash must not be source-of-claim

    Call this on every ProofRecord before treating it as valid.
    """
    claims = record.get("claims", [])
    for c in claims:
        src = (c.get("source") or "").lower()
        if (
            "hash" in src
            or "sha256" in src
            or "sha-256" in src
            or "fingerprint" in src
            or "checksum" in src
        ):
            raise AssertionError(
                f"❌ violation of 'hash must not be source-of-claim': "
                f"claim id={c.get('id')!r} cites source={src!r}. "
                f"The hash seals the proof; it does not produce claims."
            )


def assert_integrity_section_separate(record: dict) -> None:
    """Raise AssertionError if integrity fields leak into claims/trace."""
    forbidden = {"proof_trace_hash", "trace_integrity_hash", "hash"}
    for c in record.get("claims", []):
        if any(k in c for k in forbidden):
            raise AssertionError(
                f"❌ integrity field leaked into claim: {c.get('id')}"
            )
    for s in record.get("trace", []):
        if any(k in s for k in forbidden):
            raise AssertionError(
                f"❌ integrity field leaked into trace: {s.get('contract')}"
            )


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  IntegrityContract self-test")
    print("=" * 60)

    # Example: مَكْتَب (المثال المستخدم في تَصميم المستخدم)
    claims = [
        {
            "id": "template",
            "value": "مَفْعَل",
            "source": "TemplateContract:TPL-MAFAL-001",
        },
        {
            "id": "radical_trace",
            "value": ["ك", "ت", "ب"],
            "source": "RadicalTraceContract:slot_mapping",
        },
    ]
    trace = [
        {"contract": "Carrier", "result": "PASS"},
        {"contract": "Normalization", "result": "PASS"},
        {"contract": "Template", "result": "PASS"},
        {"contract": "Gate", "result": "PASS"},
    ]
    sealed = seal(claims, trace)

    record = {
        "input": "مَكْتَب",
        "status": "Certificate",
        "closure": "CLOSED",
        "claims": claims,
        "trace": trace,
        "residuals": [],
        "blockers": [],
        "integrity": asdict(sealed),
    }

    print()
    print("Record:")
    print(canonical_json(record)[:200] + "...")
    print()
    print(f"proof_trace_hash: {sealed.proof_trace_hash}")
    print()

    # القاعدة الذهبيّة — اختبار assertion
    print("--- اختبار assertion 1: hash ليس مصدر claim ---")
    try:
        assert_hash_not_source_of_claim(record)
        print("  ✓ pass — لا claim يَستند إلى hash")
    except AssertionError as e:
        print(f"  ✗ {e}")

    # اختبار سلبي: ادّعاء يَتَهَرَّب
    print()
    print("--- اختبار assertion 2: محاولة انتهاك (يجب أن تَفشل) ---")
    bad_record = dict(record)
    bad_record["claims"] = list(claims) + [{  # linter:skip
        "id": "identity",
        "value": "fake",
        "source": "sha256:abcd",  # linter:skip — intentional self-test violation
    }]
    try:
        assert_hash_not_source_of_claim(bad_record)
        print("  ✗ unexpected pass — caught nothing!")
    except AssertionError as e:
        print(f"  ✓ pass — رَفَض الانتهاك:")
        print(f"      {str(e)[:120]}")

    # اختبار سلامة الـ integrity isolation
    print()
    print("--- اختبار assertion 3: integrity لا تَتَسلَّل إلى claims ---")
    try:
        assert_integrity_section_separate(record)
        print("  ✓ pass — integrity مُنفصلة")
    except AssertionError as e:
        print(f"  ✗ {e}")

    # تَحقّق determinism
    print()
    print("--- اختبار determinism: نفس المُدخَل = نفس الـ hash ---")
    h1 = compute_proof_trace_hash(claims, trace)
    h2 = compute_proof_trace_hash(claims, trace)
    print(f"  hash1 = {h1}")
    print(f"  hash2 = {h2}")
    print(f"  متطابق؟ {'✓ pass' if h1 == h2 else '✗ FAIL'}")
