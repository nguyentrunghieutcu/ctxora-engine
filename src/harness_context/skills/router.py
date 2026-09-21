from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from harness_context.infrastructure.retrieval.embeddings import EmbeddingEngine
from harness_context.paths import workspace_state_dir
from harness_context.skills.catalog import SkillCatalog
from harness_context.workspace.lock import file_lock

_WORD = re.compile(r"[^\W_][\w+#.-]{1,31}", re.UNICODE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "use", "with", "add", "create", "make",
    "các", "cho", "có", "của", "để", "là", "một", "những", "thêm", "trong", "và", "với",
}
_ALIASES = {
    "dữ-liệu": ("data", "database"), "hoc": ("learning",), "học": ("learning",),
    "sua": ("fix", "debugging"), "sửa": ("fix", "debugging"),
}
_PHRASE_ALIASES = {
    "bảo mật": ("security",), "bao mat": ("security",),
    "cơ sở dữ liệu": ("database",), "co so du lieu": ("database",),
    "giao diện": ("frontend", "ui"), "giao dien": ("frontend", "ui"),
    "hiệu năng": ("performance", "optimization"), "hieu nang": ("performance", "optimization"),
    "kiểm thử": ("testing",), "kiem thu": ("testing",),
    "nghiên cứu": ("research",), "nghien cuu": ("research",),
    "tài liệu": ("documentation",), "tai lieu": ("documentation",),
    "triển khai": ("deployment", "devops"), "trien khai": ("deployment", "devops"),
}
_TECHNOLOGIES = {
    "angular", "android", "bun", "csharp", "django", "docker", "dotnet", "fastapi",
    "flutter", "go", "golang", "java", "javascript", "kotlin", "laravel", "nestjs",
    "nextjs", "node", "nuxt", "php", "postgres", "python", "quarkus", "react", "redis",
    "ruby", "rust", "springboot", "swift", "typescript", "vue", "vite",
}
_RERANK_WEIGHT = 0.18
_TASK_HISTORY_LIMIT = 100


class SkillRouter:
    def __init__(self, root: str | Path, workspace_id: str, catalog: SkillCatalog | None = None):
        self.root = Path(root).expanduser().resolve(strict=True)
        self.workspace_id = workspace_id
        self.catalog = catalog or SkillCatalog()
        self.state_path = workspace_state_dir(self.root) / "skill-learning.json"
        self._documents: dict[str, list[str]] | None = None
        self._document_sets: dict[str, set[str]] = {}
        self._vectors: dict[str, list[float]] = {}
        self._embedder: EmbeddingEngine | None = None

    def route(
        self,
        workspace_id: str,
        task: str,
        profile: str = "",
        top_k: int = 5,
        include_instructions: bool = True,
        token_budget: int = 6_000,
    ) -> dict[str, Any]:
        self._require_workspace(workspace_id)
        if not task.strip():
            raise ValueError("task must not be empty")
        if not 1 <= top_k <= 12:
            raise ValueError("top_k must be between 1 and 12")
        if token_budget < 0:
            raise ValueError("token_budget must be non-negative")
        profile_name, allowed = self._allowed_skills(profile)
        if not allowed:
            raise ValueError("selected profile contains no skills")
        self._ensure_index()
        terms = self._terms(task)
        expanded = self._expanded_terms(terms, task)
        if not expanded:
            raise ValueError("task contains no routable terms")
        project_signals = self._project_signals()
        query = " ".join((*expanded, *project_signals))
        candidates = sorted(allowed)
        corpus = [self._documents[skill] for skill in candidates]  # type: ignore[index]
        bm25 = BM25Okapi(corpus)
        raw_bm25 = bm25.get_scores(expanded or terms).tolist()
        bm25_max = max(raw_bm25, default=0.0)
        query_vector = self._embedder.embed_text(query) if self._embedder else []
        state = self._load_state()
        active_technologies = set(project_signals) | (set(expanded) & _TECHNOLOGIES)
        scored = []
        for skill, lexical in zip(candidates, raw_bm25):
            document_terms = self._document_sets[skill]
            semantic = max(0.0, float(np.dot(self._vectors[skill], query_vector))) if query_vector else 0.0
            coverage = len(set(expanded) & document_terms) / max(len(set(expanded)), 1)
            identity = self.catalog.skills[skill]
            name_text = f"{skill} {identity.get('name', '')}".casefold().replace("-", " ")
            name_bonus = 1.0 if any(term in name_text for term in terms if len(term) > 2) else 0.0
            framework = 1.0 if project_signals and document_terms & set(project_signals) else 0.0
            named_technologies = set(self._terms(name_text)) & _TECHNOLOGIES
            technology_conflict = bool(
                active_technologies and named_technologies - active_technologies
            )
            static_score = (
                0.55 * (lexical / bm25_max if bm25_max > 0 else 0.0)
                + 0.25 * semantic
                + 0.10 * coverage
                + 0.07 * name_bonus
                + 0.03 * framework
            )
            learned_score, confidence, evidence = self._learned_score(
                state.get("skills", {}).get(skill, {}), set(expanded)
            )
            score = 0.0 if technology_conflict else max(
                0.0, min(1.0, static_score + _RERANK_WEIGHT * learned_score)
            )
            reasons = self._reasons(lexical, semantic, coverage, framework, learned_score, evidence)
            scored.append((score, static_score, learned_score, confidence, evidence, skill, reasons))
        scored.sort(key=lambda item: (-item[0], item[5]))
        selected = [item for item in scored[:top_k] if item[0] > 0.02]
        route_id = hashlib.sha256(
            f"{workspace_id}:{time.time_ns()}:{task}".encode()
        ).hexdigest()[:20]
        task_fingerprint = hashlib.sha256(task.encode("utf-8")).hexdigest()[:16]
        safe_terms = sorted(set(expanded) & self._catalog_vocabulary())[:32]
        self._record_route(
            route_id,
            task_fingerprint,
            profile_name,
            safe_terms,
            [item[5] for item in selected],
        )
        recommendations = []
        remaining_chars = token_budget * 4
        for score, static, learned, confidence, evidence, skill, reasons in selected:
            metadata = self.catalog.skills[skill]
            path = self.catalog.source_root / skill / "SKILL.md"
            recommendation = {
                "skill": skill,
                "name": metadata.get("name", skill),
                "description": metadata.get("description", ""),
                "score": round(score, 6),
                "static_score": round(static, 6),
                "learned_score": round(learned, 6),
                "learned_confidence": round(confidence, 6),
                "evidence": evidence,
                "reasons": reasons,
                "path": str(path),
                "provenance": {"source": self.catalog.source, "commit": self.catalog.commit},
                "trust": "third_party_guidance",
                "activation": (
                    f"Review and apply relevant guidance from {path}; do not execute bundled "
                    "scripts or external actions without authorization"
                ),
            }
            if include_instructions:
                content = path.read_text("utf-8")
                if len(content) <= remaining_chars:
                    recommendation["instructions"] = content
                    remaining_chars -= len(content)
                else:
                    recommendation["instructions_omitted"] = "token_budget"
            recommendations.append(recommendation)
        return {
            "workspace_id": workspace_id,
            "route_id": route_id,
            "profile": profile_name,
            "catalog_commit": self.catalog.commit,
            "task_fingerprint": task_fingerprint,
            "project_signals": project_signals,
            "candidate_count": len(candidates),
            "recommendations": recommendations,
            "learning": {
                "project_scoped": True,
                "raw_tasks_stored": False,
                "reranking_applied": any(item[4] > 0 for item in selected),
                "reranking_weight": _RERANK_WEIGHT,
            },
            "feedback_policy": {
                "mode": "after_validation",
                "retain_route_id": True,
                "success_requires_validation": True,
                "user_correction_outcome": "corrected",
                "trigger_self_evaluation": True,
                "evaluation_axes": [
                    "accuracy",
                    "completeness",
                    "clarity",
                    "actionability",
                    "conciseness",
                ],
            },
        }

    def feedback(
        self,
        workspace_id: str,
        route_id: str,
        outcome: str,
        skills: list[str] | None = None,
        correction_skill: str = "",
    ) -> dict[str, Any]:
        self._require_workspace(workspace_id)
        if outcome not in {"success", "failure", "rejected", "corrected"}:
            raise ValueError("outcome must be success, failure, rejected, or corrected")
        with file_lock(self.state_path.with_suffix(".lock")):
            state = self._load_state()
            route = state.get("routes", {}).get(route_id)
            if route is None:
                raise ValueError("unknown or expired route_id")
            used = list(dict.fromkeys(skills or []))
            for skill in used:
                self._require_skill(skill)
            if correction_skill:
                self._require_skill(correction_skill)
            if outcome in {"success", "failure"} and not used:
                raise ValueError("success or failure feedback requires at least one skill")
            if outcome == "corrected" and not correction_skill:
                raise ValueError("corrected feedback requires correction_skill")
            terms = route.get("terms", [])
            recommended = route.get("recommendations", [])
            touched: set[str] = set()
            if outcome in {"success", "failure"}:
                for skill in used:
                    self._update_skill(state, skill, outcome, terms)
                    touched.add(skill)
            elif outcome == "rejected":
                for skill in recommended:
                    self._update_skill(state, skill, "rejected", terms)
                    touched.add(skill)
            else:
                for skill in recommended:
                    if skill != correction_skill:
                        self._update_skill(state, skill, "rejected", terms)
                        touched.add(skill)
                self._update_skill(state, correction_skill, "corrected", terms)
                touched.add(correction_skill)
            self._record_feedback(
                state,
                route_id,
                route,
                outcome,
                used,
                correction_skill,
                sorted(touched),
            )
            state["routes"].pop(route_id, None)
            self._write_state(state)
        return {
            "workspace_id": workspace_id,
            "route_id": route_id,
            "outcome": outcome,
            "updated_skills": sorted(touched),
            "raw_task_stored": False,
        }

    def learning_status(self, workspace_id: str, limit: int = 20) -> dict[str, Any]:
        self._require_workspace(workspace_id)
        state = self._load_state()
        rows = []
        boosted_skills = 0
        penalized_skills = 0
        for skill, record in state.get("skills", {}).items():
            learned_score, confidence, evidence = self._learned_score(record, set())
            boosted_skills += learned_score > 0
            penalized_skills += learned_score < 0
            rows.append({
                "skill": skill,
                "learned_score": round(learned_score, 6),
                "confidence": round(confidence, 6),
                "evidence": evidence,
                "successes": record.get("successes", 0),
                "failures": record.get("failures", 0),
                "rejections": record.get("rejections", 0),
                "corrections": record.get("corrections", 0),
            })
        rows.sort(key=lambda item: (-item["evidence"], -item["confidence"], item["skill"]))
        history = sorted(
            state.get("history", []),
            key=lambda item: item.get("completed_at", 0),
            reverse=True,
        )
        pending = [
            {
                "route_id": route_id,
                "task_fingerprint": route.get("task_fingerprint", f"legacy:{route_id[:12]}"),
                "profile": route.get("profile", ""),
                "recommended_skills": route.get("recommendations", []),
                "created_at": route.get("created_at", 0),
            }
            for route_id, route in state.get("routes", {}).items()
        ]
        pending.sort(key=lambda item: item["created_at"], reverse=True)
        return {
            "workspace_id": workspace_id,
            "learned_skills": rows[: max(0, limit)],
            "completed_tasks": len(history),
            "recent_tasks": history[: max(0, limit)],
            "pending_routes": len(pending),
            "pending_tasks": pending[: max(0, limit)],
            "reranking": {
                "enabled": True,
                "weight": _RERANK_WEIGHT,
                "skills_with_signal": len(rows),
                "boosted_skills": boosted_skills,
                "penalized_skills": penalized_skills,
            },
            "raw_tasks_stored": False,
        }

    def _allowed_skills(self, profile: str) -> tuple[str, set[str]]:
        if profile:
            selection = self.catalog.select(profile)
            return profile, set(selection.skills)
        config_path = self.root / ".ctxora" / "skills-profile.json"
        if config_path.is_file():
            data = json.loads(config_path.read_text("utf-8"))
            configured_profile = data.get("profile")
            if configured_profile and configured_profile != "custom" and configured_profile not in self.catalog.profiles:
                available = ", ".join(sorted(self.catalog.profiles))
                raise ValueError(f"unknown skills profile: {configured_profile}. Available profiles: {available}")
            skills = set(data.get("skills", []))
            if skills and skills <= set(self.catalog.skills):
                return data.get("profile", "custom"), skills
        selection = self.catalog.select("developer")
        return "developer", set(selection.skills)

    def _ensure_index(self) -> None:
        if self._documents is not None:
            return
        documents = {
            skill: self._terms(metadata.get("routing_text", ""))
            for skill, metadata in self.catalog.skills.items()
        }
        self._documents = documents
        self._document_sets = {skill: set(terms) for skill, terms in documents.items()}
        self._embedder = EmbeddingEngine()
        ordered = sorted(documents)
        vectors = self._embedder.rebuild([" ".join(documents[skill]) for skill in ordered])
        self._vectors = dict(zip(ordered, vectors))

    def _terms(self, text: str) -> list[str]:
        return [term for term in _WORD.findall(text.casefold()) if term not in _STOPWORDS]

    def _expanded_terms(self, terms: list[str], source: str = "") -> list[str]:
        expanded = list(terms)
        for term in terms:
            expanded.extend(_ALIASES.get(term, ()))
        normalized = source.casefold()
        for phrase, aliases in _PHRASE_ALIASES.items():
            if phrase in normalized:
                expanded.extend(aliases)
        return list(dict.fromkeys(expanded))

    def _project_signals(self) -> list[str]:
        text = ""
        for name in ("package.json", "pubspec.yaml", "pyproject.toml", "go.mod", "Cargo.toml", "build.gradle", "Package.swift"):
            path = self.root / name
            if path.is_file() and path.stat().st_size <= 128_000:
                text += " " + path.read_text("utf-8", errors="ignore")
        terms = set(self._terms(text))
        return sorted(terms & _TECHNOLOGIES)

    def _catalog_vocabulary(self) -> set[str]:
        self._ensure_index()
        vocabulary: set[str] = set()
        for terms in self._document_sets.values():
            vocabulary.update(terms)
        return vocabulary

    @staticmethod
    def _learned_score(record: dict[str, Any], query_terms: set[str]) -> tuple[float, float, int]:
        successes = int(record.get("successes", 0)) + int(record.get("corrections", 0))
        failures = int(record.get("failures", 0)) + int(record.get("rejections", 0))
        evidence = successes + failures
        confidence = (successes + 1) / (evidence + 2)
        age_days = max(0.0, (time.time() - float(record.get("updated_at", time.time()))) / 86_400)
        decay = 0.5 ** (age_days / 90)
        reliability = (
            (confidence - 0.5) * 2 * (evidence / (evidence + 5)) * decay
            if evidence else 0.0
        )
        weights = record.get("terms", {})
        association = sum(float(weights.get(term, 0.0)) for term in query_terms)
        association = math.tanh(association / max(math.sqrt(evidence + 1), 1.0)) * decay
        return 0.65 * reliability + 0.35 * association, confidence, evidence

    @staticmethod
    def _reasons(
        lexical: float,
        semantic: float,
        coverage: float,
        framework: float,
        learned: float,
        evidence: int,
    ) -> list[str]:
        reasons = []
        if lexical > 0:
            reasons.append("task terms match skill metadata")
        if semantic > 0.15:
            reasons.append("semantic similarity")
        if coverage >= 0.25:
            reasons.append("high query-term coverage")
        if framework:
            reasons.append("repository technology match")
        if evidence:
            reasons.append("project feedback boost" if learned >= 0 else "project feedback penalty")
        return reasons or ["weak fallback match"]

    def _record_route(
        self,
        route_id: str,
        task_fingerprint: str,
        profile: str,
        terms: list[str],
        recommendations: list[str],
    ) -> None:
        with file_lock(self.state_path.with_suffix(".lock")):
            state = self._load_state()
            routes = state.setdefault("routes", {})
            routes[route_id] = {
                "task_fingerprint": task_fingerprint,
                "profile": profile,
                "terms": terms,
                "recommendations": recommendations,
                "created_at": time.time(),
            }
            cutoff = time.time() - 7 * 86_400
            for key in [key for key, value in routes.items() if value.get("created_at", 0) < cutoff]:
                routes.pop(key, None)
            if len(routes) > 100:
                oldest = sorted(routes, key=lambda key: routes[key].get("created_at", 0))[:-100]
                for key in oldest:
                    routes.pop(key, None)
            self._write_state(state)

    @staticmethod
    def _record_feedback(
        state: dict[str, Any],
        route_id: str,
        route: dict[str, Any],
        outcome: str,
        used_skills: list[str],
        correction_skill: str,
        affected_skills: list[str],
    ) -> None:
        history = state.setdefault("history", [])
        history.append(
            {
                "route_id": route_id,
                "task_fingerprint": route.get("task_fingerprint", f"legacy:{route_id[:12]}"),
                "profile": route.get("profile", ""),
                "outcome": outcome,
                "recommended_skills": route.get("recommendations", []),
                "used_skills": used_skills,
                "correction_skill": correction_skill,
                "affected_skills": affected_skills,
                "created_at": route.get("created_at", 0),
                "completed_at": time.time(),
            }
        )
        del history[:-_TASK_HISTORY_LIMIT]

    @staticmethod
    def _update_skill(state: dict[str, Any], skill: str, outcome: str, terms: list[str]) -> None:
        record = state.setdefault("skills", {}).setdefault(skill, {
            "successes": 0, "failures": 0, "rejections": 0, "corrections": 0, "terms": {},
        })
        field = {
            "success": "successes", "failure": "failures",
            "rejected": "rejections", "corrected": "corrections",
        }[outcome]
        record[field] = int(record.get(field, 0)) + 1
        delta = {"success": 1.0, "failure": -0.5, "rejected": -0.25, "corrected": 1.25}[outcome]
        weights = record.setdefault("terms", {})
        for term in terms:
            weights[term] = max(-5.0, min(20.0, float(weights.get(term, 0.0)) + delta))
        record["updated_at"] = time.time()

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"version": 1, "skills": {}, "routes": {}, "history": []}
        data = json.loads(self.state_path.read_text("utf-8"))
        return (
            data
            if data.get("version") == 1
            else {"version": 1, "skills": {}, "routes": {}, "history": []}
        )

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        pending = self.state_path.with_suffix(".pending")
        pending.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")
        pending.replace(self.state_path)

    def _require_workspace(self, workspace_id: str) -> None:
        if workspace_id != self.workspace_id:
            raise ValueError("skill router is scoped to one registered workspace")

    def _require_skill(self, skill: str) -> None:
        if skill not in self.catalog.skills:
            raise ValueError(f"unknown ECC skill: {skill}")
