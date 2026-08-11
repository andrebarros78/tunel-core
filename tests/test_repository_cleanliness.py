from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".ps1", ".xml", ".json", ".md", ".toml", ".yml", ".yaml"}


def forbidden_patterns() -> tuple[str, ...]:
    return (
        "D:" + "\\Projetos",
        "C:" + "\\Projetos",
        "windows" + "-mcp",
        "WINDOWS" + "-MCP",
        "Action" + " Gateway",
        "P" + "ipo",
    )


def test_repository_has_no_application_or_legacy_path_bindings():
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="strict")
        for pattern in forbidden_patterns():
            if pattern in text:
                violations.append(f"{path.relative_to(ROOT)}: {pattern}")
    assert violations == [], "Forbidden TUNEL-CORE bindings found:\n" + "\n".join(violations)
