"""Cross-validation: provider_backend direct targets must exist in the real CLIs.

The cutover correctness contract is:
  every value in provider_backend.DIRECT_MODEL[provider] must be a valid key in
  the corresponding direct CLI's MODEL_MAP (gemini-3.py / openai-cli.py), AND an
  accepted --model argparse choice.

These CLIs import google.genai / openai at module top and sys.exit(1) when those
packages are absent, so we cannot spec-import them in CI. Instead we AST-parse
the source to extract MODEL_MAP keys and the --model choices without executing
the import side effects.
"""

import ast
import importlib.util
from pathlib import Path

import pytest

TOOLS = Path(__file__).parent.parent / "tools"

_pb_path = TOOLS / "provider_backend.py"
_spec = importlib.util.spec_from_file_location("provider_backend", _pb_path)
provider_backend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(provider_backend)


def _module_ast(filename: str) -> ast.Module:
    return ast.parse((TOOLS / filename).read_text(encoding="utf-8"))


def _class_assign_dict(tree: ast.Module, class_name: str, attr: str) -> dict:
    """Extract a class-level dict-literal assignment (e.g. MODEL_MAP) by name."""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == attr:
                            return ast.literal_eval(stmt.value)
    raise AssertionError(f"{class_name}.{attr} not found")


def _argparse_model_choices(tree: ast.Module) -> set:
    """Find the choices=[...] list literal of the --model / -m add_argument call."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "add_argument":
            flags = {a.value for a in node.args if isinstance(a, ast.Constant)}
            if "--model" in flags or "-m" in flags:
                for kw in node.keywords:
                    if kw.arg == "choices":
                        return set(ast.literal_eval(kw.value))
    raise AssertionError("--model choices not found")


GEMINI_AST = _module_ast("gemini-3.py")
OPENAI_AST = _module_ast("openai-cli.py")

GEMINI_MAP = _class_assign_dict(GEMINI_AST, "GeminiProvider", "MODEL_MAP")
OPENAI_MAP = _class_assign_dict(OPENAI_AST, "OpenAIProvider", "MODEL_MAP")
GEMINI_CHOICES = _argparse_model_choices(GEMINI_AST)
OPENAI_CHOICES = _argparse_model_choices(OPENAI_AST)


class TestDirectModelTargetsExist:
    @pytest.mark.parametrize(
        "target", sorted(set(provider_backend.DIRECT_MODEL["gemini"].values()))
    )
    def test_gemini_target_in_model_map(self, target):
        assert target in GEMINI_MAP, f"gemini direct target '{target}' missing from MODEL_MAP"

    @pytest.mark.parametrize(
        "target", sorted(set(provider_backend.DIRECT_MODEL["gemini"].values()))
    )
    def test_gemini_target_is_argparse_choice(self, target):
        assert target in GEMINI_CHOICES, f"gemini '{target}' not an accepted --model choice"

    @pytest.mark.parametrize(
        "target", sorted(set(provider_backend.DIRECT_MODEL["openai"].values()))
    )
    def test_openai_target_in_model_map(self, target):
        assert target in OPENAI_MAP, f"openai direct target '{target}' missing from MODEL_MAP"

    @pytest.mark.parametrize(
        "target", sorted(set(provider_backend.DIRECT_MODEL["openai"].values()))
    )
    def test_openai_target_is_argparse_choice(self, target):
        assert target in OPENAI_CHOICES, f"openai '{target}' not an accepted --model choice"


class TestDirectCliNamesSane:
    def test_direct_cli_targets(self):
        assert provider_backend.DIRECT_CLI["gemini"] == "gemini-3"
        assert provider_backend.DIRECT_CLI["openai"] == "openai-cli"

    def test_gemini_flash_latest_resolves_to_stable_alias(self):
        """3.5-flash → flash-latest → gemini-flash-latest (stable, not a preview pin).
        Guards the EOL-avoidance decision from the v3.6 cutover plan."""
        assert GEMINI_MAP["flash-latest"] == "gemini-flash-latest"

    def test_openai_gpt55_resolves_to_gpt_5_5(self):
        assert OPENAI_MAP["gpt55"] == "gpt-5.5"
