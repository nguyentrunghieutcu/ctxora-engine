from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness_context.api.v2 import PrepareContextRequest
from harness_context.bootstrap import build_container
from harness_context.skills import SkillCatalog, SkillRouter
from harness_context.workspace.identity import workspace_identity


class SkillRouterTests(unittest.TestCase):
    def router(self, root: Path) -> SkillRouter:
        return SkillRouter(root, workspace_identity(root), SkillCatalog())

    def test_routes_react_performance_with_project_signals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                '{"dependencies":{"react":"19","next":"15"}}', "utf-8"
            )
            router = self.router(root)
            result = router.route(
                router.workspace_id,
                "Fix React hydration performance and unnecessary rerenders",
                "developer",
                top_k=3,
                include_instructions=False,
            )
            self.assertEqual("react-performance", result["recommendations"][0]["skill"])
            self.assertIn("react", result["project_signals"])
            self.assertEqual("third_party_guidance", result["recommendations"][0]["trust"])
            self.assertEqual("after_validation", result["feedback_policy"]["mode"])
            self.assertTrue(result["feedback_policy"]["success_requires_validation"])

    def test_routes_vietnamese_fastapi_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            router = self.router(root)
            result = router.route(
                router.workspace_id,
                "sửa lỗi và tối ưu hiệu năng API FastAPI bằng kiểm thử",
                "developer",
                top_k=3,
                include_instructions=False,
            )
            self.assertEqual("fastapi-patterns", result["recommendations"][0]["skill"])

    def test_flutter_project_penalizes_unrelated_framework_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pubspec.yaml").write_text(
                "dependencies:\n  flutter:\n    sdk: flutter\n", "utf-8"
            )
            router = self.router(root)
            result = router.route(
                router.workspace_id,
                "Review Flutter provider, Firebase authorization, tests, and deployment readiness",
                "developer",
                top_k=5,
                include_instructions=False,
            )
            skills = [item["skill"] for item in result["recommendations"]]
            self.assertIn("flutter", result["project_signals"])
            self.assertEqual("flutter-dart-code-review", skills[0])
            self.assertNotIn("django-verification", skills)
            self.assertNotIn("laravel-verification", skills)

    def test_uses_installed_custom_profile_as_candidate_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = SkillCatalog()
            selection = catalog.select(
                "minimal",
                remove_modules=("workflow-quality",),
                add_skills=("api-design",),
            )
            catalog.write_selection(root, selection)
            router = SkillRouter(root, workspace_identity(root), catalog)
            result = router.route(
                router.workspace_id, "Design a stable REST API contract", include_instructions=False
            )
            self.assertEqual(1, result["candidate_count"])
            self.assertEqual("api-design", result["recommendations"][0]["skill"])

    def test_feedback_changes_learned_score_without_storing_raw_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            router = self.router(root)
            secret_task = "Design backend API sk-live-supersecret"
            first = router.route(
                router.workspace_id, secret_task, "developer", top_k=5,
                include_instructions=False,
            )
            pending = router.learning_status(router.workspace_id)
            self.assertEqual(1, pending["pending_routes"])
            self.assertEqual(
                first["task_fingerprint"],
                pending["pending_tasks"][0]["task_fingerprint"],
            )
            skill = first["recommendations"][0]["skill"]
            feedback = router.feedback(
                router.workspace_id, first["route_id"], "success", [skill]
            )
            self.assertFalse(feedback["raw_task_stored"])
            state = router.state_path.read_text("utf-8")
            self.assertNotIn(secret_task, state)
            self.assertNotIn("sk-live-supersecret", state)
            second = router.route(
                router.workspace_id, secret_task, "developer", top_k=5,
                include_instructions=False,
            )
            learned = next(item for item in second["recommendations"] if item["skill"] == skill)
            self.assertGreater(learned["learned_score"], 0)
            self.assertGreater(learned["score"], learned["static_score"])
            status = router.learning_status(router.workspace_id)
            self.assertEqual(1, status["learned_skills"][0]["evidence"])
            self.assertFalse(json.loads(router.state_path.read_text("utf-8")).get("raw_task"))

    def test_learning_status_tracks_completed_tasks_and_reranking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            router = self.router(root)
            secret_task = "Design a stable backend API sk-private-task"
            first = router.route(
                router.workspace_id,
                secret_task,
                "developer",
                top_k=3,
                include_instructions=False,
            )
            skill = first["recommendations"][0]["skill"]
            router.feedback(router.workspace_id, first["route_id"], "success", [skill])
            status = router.learning_status(router.workspace_id)
            self.assertEqual(1, status["completed_tasks"])
            self.assertEqual("success", status["recent_tasks"][0]["outcome"])
            self.assertEqual([skill], status["recent_tasks"][0]["used_skills"])
            self.assertEqual(1, status["reranking"]["skills_with_signal"])
            self.assertEqual(1, status["reranking"]["boosted_skills"])
            self.assertEqual([], status["pending_tasks"])
            encoded = router.state_path.read_text("utf-8")
            self.assertNotIn(secret_task, encoded)
            self.assertNotIn("sk-private-task", encoded)

    def test_prepare_context_routes_skills_automatically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# React application", "utf-8")
            (root / "package.json").write_text('{"dependencies":{"react":"19","next":"15"}}', "utf-8")
            container = build_container(root)
            workspace_id = next(iter(container.engine.states))
            container.refresh.execute(workspace_id)
            result = container.context.prepare(PrepareContextRequest(
                workspace_id=workspace_id,
                query="Fix React hydration performance and unnecessary rerenders",
                available_input_tokens=4_000,
            ))
            skills = result.diagnostics["skills"]
            self.assertTrue(skills["enabled"])
            self.assertTrue(skills["route_id"])
            self.assertEqual("react-performance", skills["recommendations"][0]["skill"])
            self.assertNotIn("instructions", skills["recommendations"][0])
            self.assertEqual("after_validation", skills["feedback_policy"]["mode"])

    def test_feedback_rejects_wrong_workspace_and_invalid_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            router = self.router(Path(directory))
            with self.assertRaisesRegex(ValueError, "scoped to one registered workspace"):
                router.route("wrong", "Design an API")
            with self.assertRaisesRegex(ValueError, "unknown or expired route_id"):
                router.feedback(router.workspace_id, "missing", "rejected")


if __name__ == "__main__":
    unittest.main()
