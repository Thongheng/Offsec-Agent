"""Discovery engine — runnable techniques, not a prose menu (invariant I4)."""
from . import authz_matrix, lifecycle, outlier, seam

MODULES = {"outlier": outlier.run, "authz_matrix": authz_matrix.run, "lifecycle": lifecycle.run}
PURE = {"seam": seam.diff}
