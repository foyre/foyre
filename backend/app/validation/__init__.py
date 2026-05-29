"""Validation pipeline execution engine.

Mirrors the layout of `app.provisioning`: a runner that does long-running
work in a background thread, step executors that perform the actual
checks against a validation environment, and small typed value objects
that flow between them.
"""
