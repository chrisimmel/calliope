"""/v3/admin/* routers — admin-only views replacing Thoth + Piccolo Admin."""

from calliope2.api.v3.admin import actions, resources, search, stories

__all__ = ["actions", "resources", "search", "stories"]
