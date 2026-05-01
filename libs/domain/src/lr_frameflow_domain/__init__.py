"""Domain layer: job kinds and lifecycle states (transport- and ORM-free)."""

from lr_frameflow_domain.jobs import JobKind, JobStatus

__all__ = ["JobKind", "JobStatus"]
