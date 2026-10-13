# Historical rendering inputs

These snapshots retain the exact `src/` and `deploy/` inputs from the original
public v2.0.2.3 and v2.0.2.11 source archives. Both original archives have identical
deployment resources, stored once here. The manifest records each original
archive SHA-256, snapshot SHA-256 and every input file SHA-256.

Release cleanup can remove older release entries without removing these mandatory
historical comparisons. The current GLES fixture, scenes and assertions still run
against both historical source trees. Missing or modified snapshots fail validation.
These files contain public application resources, not user profiles or diagnostics.
