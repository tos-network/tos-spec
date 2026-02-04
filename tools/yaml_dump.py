"""Shared YAML dump helpers with Rust serde_yaml preference."""

from __future__ import annotations

from pathlib import Path
import json

import yaml


class PlainDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=None)


PlainDumper.add_representer(str, _str_representer)


def dump_yaml(data: dict) -> str:
    try:
        import tos_yaml  # type: ignore  # noqa: WPS433

        return tos_yaml.dump_yaml(json.dumps(data, separators=(",", ":"), ensure_ascii=True))
    except Exception:
        return yaml.dump(data, Dumper=PlainDumper, sort_keys=False, width=4096)


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(dump_yaml(data))
