from typing import Callable, Dict

class FeatureRegistry:
    def __init__(self):
        self._registry: Dict[str, Dict[str, Callable]] = {}

    def register(self, name: str, version: str, func: Callable) -> None:
        if name not in self._registry:
            self._registry[name] = {}
        self._registry[name][version] = func
        print(f"Registered feature: {name} v{version}")

    def get_feature(self, name: str, version: str) -> Optional[Callable]:
        return self._registry.get(name, {}).get(version)
