"""Entry points based registry management."""
import contextlib
from importlib.metadata import entry_points


def get_entry_points(group):
    """Get the list of pytest_unique entry points."""
    try:
        return entry_points().select(group=group)
    except AttributeError:
        # Backward compatibility with Python 3.8.
        return entry_points().get(group, [])


def registry_load(name, registry=None):
    """Find all installed entry points."""
    if registry is None:
        registry = {}

    group = f"permaculture.{name}"
    for entry_point in get_entry_points(group):
        entry = entry_point.load()
        registry_add(name, entry_point.name, entry, registry)

    return registry


def registry_add(group, name, entry, registry=None):
    """Add an entry to a registry.

    :param group: Group of the entry.
    :param name: Name of the entry.
    :param entry: Entry to add.
    :param registry: Optional registry to update.
    :return: A registry with the entry.
    """
    if registry is None:
        registry = {
            group: {},
        }
    else:
        registry.setdefault(group, {})

    registry[group][name] = entry
    return registry


def registry_remove(group, name, registry=None):
    """Remove an entry from a registry.

    If the entry doesn't exist, return silently.

    :param group: Group of the entry.
    :param name: Name of the entry.
    :param registry: Optional registry to update.
    """
    if registry is not None:
        with contextlib.suppress(KeyError):
            del registry[group][name]


def registry_get(group, name, registry=None):
    """Get an entry from a registry.

    If the registry is not defined or the group is not in the registry,
    the registry is loaded again.

    :param group: Group of the entry.
    :param name: Name of the entry.
    :param registry: Optional registry to get from.
    :raises KeyError: If not found.
    """
    if registry is None or group not in registry:
        registry = registry_load(group, registry)

    return registry[group][name]
