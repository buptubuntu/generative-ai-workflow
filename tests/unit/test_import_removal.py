"""Verify that all v0.1.x Step names are permanently removed (no compat aliases).

These tests ensure that importing any removed symbol raises ImportError or
AttributeError, confirming the hard breaking rename to Node in v0.2.0.
"""

from __future__ import annotations

import importlib

import pytest


class TestStepModuleRemoved:
    """The generative_ai_workflow.step module must not exist."""

    def test_step_module_import_raises(self) -> None:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("generative_ai_workflow.step")


class TestRemovedTopLevelSymbols:
    """All v0.1.x Step symbols must be absent from the public API."""

    def _get_public_api(self):
        import generative_ai_workflow
        return generative_ai_workflow

    def test_workflow_step_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "WorkflowStep"), "WorkflowStep must not be exported"

    def test_llm_step_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "LLMStep"), "LLMStep must not be exported"

    def test_transform_step_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "TransformStep"), "TransformStep must not be exported"

    def test_conditional_step_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "ConditionalStep"), "ConditionalStep must not be exported"

    def test_step_error_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "StepError"), "StepError must not be exported"

    def test_step_context_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "StepContext"), "StepContext must not be exported"

    def test_step_result_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "StepResult"), "StepResult must not be exported"

    def test_step_status_removed(self) -> None:
        api = self._get_public_api()
        assert not hasattr(api, "StepStatus"), "StepStatus must not be exported"


class TestNodeSymbolsPresent:
    """All v0.2.0 Node symbols must be present in the public API."""

    def _get_public_api(self):
        import generative_ai_workflow
        return generative_ai_workflow

    def test_workflow_node_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "WorkflowNode")

    def test_llm_node_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "LLMNode")

    def test_transform_node_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "TransformNode")

    def test_conditional_node_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "ConditionalNode")

    def test_node_error_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "NodeError")

    def test_node_context_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "NodeContext")

    def test_node_result_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "NodeResult")

    def test_node_status_present(self) -> None:
        api = self._get_public_api()
        assert hasattr(api, "NodeStatus")


class TestWorkflowNodesParameter:
    """Workflow must accept nodes= and reject steps= parameter."""

    def test_workflow_accepts_nodes_param(self) -> None:
        from generative_ai_workflow import TransformNode, Workflow
        w = Workflow(nodes=[TransformNode(name="t", transform=lambda d: {})])
        assert len(w.nodes) == 1

    def test_workflow_has_nodes_attribute(self) -> None:
        from generative_ai_workflow import TransformNode, Workflow
        w = Workflow(nodes=[TransformNode(name="t", transform=lambda d: {})])
        assert hasattr(w, "nodes")
        assert not hasattr(w, "steps")

    def test_workflow_rejects_steps_param(self) -> None:
        from generative_ai_workflow import TransformNode, Workflow
        with pytest.raises(TypeError):
            Workflow(steps=[TransformNode(name="t", transform=lambda d: {})])  # type: ignore[call-arg]
