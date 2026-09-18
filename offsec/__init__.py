"""offsec-agent v2 — structured, gate-enforced bug bounty workflow.

Architecture invariants:
  I1  One append-only event log per target; all status is derived, never hand-edited.
  I2  Machine-enforced engagement gates + per-feature slice pipeline.
  I3  Yield is computed (accepted-shapes x enabled-features x reachable-contexts).
  I4  Every discovery technique is a runnable module, not a prose menu.
"""

__version__ = "2.0.0"
