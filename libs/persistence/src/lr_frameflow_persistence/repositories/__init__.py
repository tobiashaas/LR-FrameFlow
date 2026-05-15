"""Repository implementations for all domain entities."""

from lr_frameflow_persistence.repositories.edit_results import EditResultRepository
from lr_frameflow_persistence.repositories.feature_vectors import FeatureVectorRepository
from lr_frameflow_persistence.repositories.jobs import JobRepository
from lr_frameflow_persistence.repositories.photos import PhotoRepository
from lr_frameflow_persistence.repositories.profiles import ProfileRepository

__all__ = [
    "EditResultRepository",
    "FeatureVectorRepository",
    "JobRepository",
    "PhotoRepository",
    "ProfileRepository",
]
