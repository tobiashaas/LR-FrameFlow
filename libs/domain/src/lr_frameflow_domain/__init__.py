"""Domain layer: job kinds, lifecycle states, profile states (transport- and ORM-free)."""

from lr_frameflow_domain.jobs import JobKind, JobStatus
from lr_frameflow_domain.profiles import ProfileStatus

__all__ = ["JobKind", "JobStatus", "ProfileStatus"]
