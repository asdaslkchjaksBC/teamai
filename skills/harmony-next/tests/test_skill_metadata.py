from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
SKILL_PATH = SKILL_ROOT / "SKILL.md"
README_PATH = REPO_ROOT / "README.md"
README_EN_PATH = REPO_ROOT / "README_en.md"
EMULATOR_PLAYBOOK_PATH = SKILL_ROOT / "references" / "ideGuides" / "DevEco模拟器私有接口与AI自动化.md"
EMPTY_ABILITY_TEMPLATE_ROOT = SKILL_ROOT / "references" / "templates" / "empty-ability-app"
MINIMAL_SCAFFOLD_DOC_PATH = SKILL_ROOT / "references" / "quickStart" / "ets" / "minimal-project-scaffold.md"
SCRIPT_ROOT = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

import sync_release_version  # noqa: E402


class SkillMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_text = SKILL_PATH.read_text(encoding="utf-8")
        self.readme_text = README_PATH.read_text(encoding="utf-8")
        self.readme_en_text = README_EN_PATH.read_text(encoding="utf-8")
        self.emulator_playbook_text = EMULATOR_PLAYBOOK_PATH.read_text(encoding="utf-8")
        self.minimal_scaffold_text = MINIMAL_SCAFFOLD_DOC_PATH.read_text(encoding="utf-8")

    def test_skill_exposes_current_version_for_agents(self) -> None:
        metadata_version = re.search(r"version:\s*\"(\d+\.\d+\.\d+)\"", self.skill_text)
        visible_version = re.search(r"Current local skill version:\s*`v\d+\.\d+\.\d+`", self.skill_text)
        hidden_version = re.search(r"<!-- version:\s*(\d+\.\d+\.\d+)\s*-->", self.skill_text)

        self.assertIsNotNone(metadata_version)
        self.assertIsNotNone(visible_version)
        self.assertIsNotNone(hidden_version)
        self.assertEqual(metadata_version.group(1), hidden_version.group(1))
        self.assertIn(f"`v{metadata_version.group(1)}`", visible_version.group(0))

    def test_readme_release_badges_match_skill_version(self) -> None:
        metadata_version = re.search(r"version:\s*\"(\d+\.\d+\.\d+)\"", self.skill_text)
        self.assertIsNotNone(metadata_version)

        tag_version = f"v{metadata_version.group(1)}"
        for text in [self.readme_text, self.readme_en_text]:
            with self.subTest(readme=text[:20]):
                self.assertIn(f"release-{tag_version}-1f6feb", text)
                self.assertIn(f"releases/tag/{tag_version}", text)

    def test_readmes_have_language_switches(self) -> None:
        self.assertIn("语言：中文 | [English](./README_en.md)", self.readme_text)
        self.assertIn("Language: English | [中文](./README.md)", self.readme_en_text)

    def test_readmes_document_official_codex_skill_locations(self) -> None:
        required_readme_fragments = [
            "官方 Codex Agent Skills 文档",
            "https://developers.openai.com/codex/skills",
            "$CWD/.agents/skills/harmony-next",
            "$CWD/../.agents/skills/harmony-next",
            "$REPO_ROOT/.agents/skills/harmony-next",
            "$HOME/.agents/skills/harmony-next",
            "/etc/codex/skills/harmony-next",
            "可安装分发单元是 Codex plugin",
        ]
        required_readme_en_fragments = [
            "official Codex Agent Skills docs",
            "https://developers.openai.com/codex/skills",
            "$CWD/.agents/skills/harmony-next",
            "$CWD/../.agents/skills/harmony-next",
            "$REPO_ROOT/.agents/skills/harmony-next",
            "$HOME/.agents/skills/harmony-next",
            "/etc/codex/skills/harmony-next",
            "plugins are the installable distribution unit",
        ]

        for fragment in required_readme_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.readme_text)
        for fragment in required_readme_en_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.readme_en_text)

    def test_skill_documents_freshness_and_installation_paths(self) -> None:
        required_fragments = [
            "Reference snapshot:",
            "not live web docs",
            "GitHub Releases or nightly",
            "Huawei online docs",
            "Install/update entrypoints:",
            "gemini skills install",
            "Claude.ai",
            "Claude Code",
            "Codex",
            "$REPO_ROOT/.agents/skills/harmony-next",
            "$HOME/.agents/skills/harmony-next",
            "/etc/codex/skills/harmony-next",
            "package it as a Codex plugin",
        ]

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.skill_text)

    def test_emulator_automation_policy_is_non_interactive(self) -> None:
        required_skill_fragments = [
            "HARMONY_NEXT_AUTOMATION_POLICY",
            "readonly",
            "evidence",
            "automation",
            "diagnostic",
            "break-glass",
            "blocked",
            "missingConfig",
            "requiredMode",
            "用户默认拥有完整执行权限",
        ]
        required_playbook_fragments = [
            "## 自动化策略模型",
            "riskLevel",
            "policy",
            "operation",
            "target",
            "artifacts",
            "redactionStatus",
            "sourceCommand",
            "artifactDir",
            ".harmony-next-policy.json",
            "--policy <readonly|evidence|automation|diagnostic|break-glass>",
            "HARMONY_NEXT_AUTOMATION_POLICY",
            "blocked",
            "missingConfig",
            "requiredMode",
            "break-glass",
            "用户默认拥有完整执行权限",
            "不是权限不足",
        ]
        required_readme_fragments = [
            "非交互自动化策略",
            "HARMONY_NEXT_AUTOMATION_POLICY",
            "machine-readable blocked",
            "策略是执行模式，不是授权门槛",
        ]
        required_readme_en_fragments = [
            "non-interactive automation policy",
            "HARMONY_NEXT_AUTOMATION_POLICY",
            "machine-readable blocked",
            "policy is an execution mode, not an authorization gate",
        ]
        forbidden_fragments = [
            "需要用户确认",
            "人工确认",
            "预授权",
            "human confirmation",
            "authorization gate",
            "forbidden",
            "requiredPolicy",
        ]

        for fragment in required_skill_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.skill_text)
        for fragment in required_playbook_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.emulator_playbook_text)
        for fragment in required_readme_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.readme_text)
        for fragment in required_readme_en_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.readme_en_text)
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, self.skill_text)
                self.assertNotIn(fragment, self.emulator_playbook_text)

    def test_tooling_script_skills_are_routed_and_documented(self) -> None:
        required_skill_fragments = [
            "## Tooling Script Skills",
            "`commandline_tools_manager.py`",
            "`hvd_manager.py`",
            "Agent first command",
            "User handoff",
            "launch --name <hvd> --image-root <dir> --trace-name <name>",
            "download center page URL",
            "HVD image download",
        ]
        required_emulator_fragments = [
            "## HVD 管理 CLI",
            "先运行 `doctor --json`",
            "跨机器分发",
            "HARMONY_HVD_ROOT",
            "socketConnected=true",
            "traceBytesRead",
            "emulator.launch",
            "download-image",
        ]

        for fragment in required_skill_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.skill_text)
        for fragment in required_emulator_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.emulator_playbook_text)

    def test_emulator_proxy_capture_guidance_is_external_user_facing(self) -> None:
        required_skill_fragments = [
            "simulator traffic capture",
            "HTTP proxy tools",
            "NetworkKit proxy routing",
            "transparent interception",
        ]
        required_playbook_fragments = [
            "## 模拟器抓包与代理诊断",
            "面向使用者",
            "10.0.2.15",
            "10.0.2.2",
            "显式 HTTP 代理",
            "抓包工具",
            "setAppHttpProxy",
            "usingProxy: true",
            "Mac 侧中转脚本",
            "不能透明接管全部流量",
            "VpnExtension",
            "调试目标应用",
        ]
        required_readme_fragments = [
            "模拟器抓包与代理诊断",
            "抓包工具",
            "10.0.2.2:9090",
            "应用级代理",
            "透明抓包",
        ]
        required_readme_en_fragments = [
            "emulator traffic capture and proxy diagnostics",
            "HTTP proxy capture tools",
            "10.0.2.2:9090",
            "app-level proxy",
            "transparent interception",
        ]

        for fragment in required_skill_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.skill_text)
        for fragment in required_playbook_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.emulator_playbook_text)
        for fragment in required_readme_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.readme_text)
        for fragment in required_readme_en_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.readme_en_text)

    def test_empty_ability_template_is_copyable_for_smoke_tests(self) -> None:
        required_paths = [
            "README.md",
            "oh-package.json5",
            "package.json",
            "build-profile.json5",
            "hvigorfile.ts",
            "hvigor/hvigor-config.json5",
            "AppScope/app.json5",
            "AppScope/resources/base/element/string.json",
            "AppScope/resources/base/media/app_icon.png",
            "entry/oh-package.json5",
            "entry/build-profile.json5",
            "entry/hvigorfile.ts",
            "entry/src/main/module.json5",
            "entry/src/main/ets/entryability/EntryAbility.ets",
            "entry/src/main/ets/components/SmokeCounter.ets",
            "entry/src/main/ets/pages/Index.ets",
            "entry/src/main/resources/base/element/color.json",
            "entry/src/main/resources/base/element/float.json",
            "entry/src/main/resources/base/element/string.json",
            "entry/src/main/resources/base/profile/main_pages.json",
        ]
        required_fragments = [
            "references/templates/empty-ability-app",
            "com.example.emptyability",
            "EntryAbility",
            "5.0.0(12)",
            "6.0.2(22)",
            "DEVECO_SDK_HOME=/Applications/DevEco-Studio.app/Contents/sdk",
            "ohpm install",
            "hvigorw --mode module",
            "startWindowIcon",
            "uitest dumpLayout",
            "uitest uiInput click",
            "Harmony Smoke Tapped",
            "smoke-increment",
            "SmokeCounter",
        ]

        for relative_path in required_paths:
            with self.subTest(path=relative_path):
                self.assertTrue((EMPTY_ABILITY_TEMPLATE_ROOT / relative_path).is_file())

        app_json = json.loads((EMPTY_ABILITY_TEMPLATE_ROOT / "AppScope" / "app.json5").read_text(encoding="utf-8"))
        module_json = json.loads((EMPTY_ABILITY_TEMPLATE_ROOT / "entry" / "src" / "main" / "module.json5").read_text(encoding="utf-8"))
        build_profile = json.loads((EMPTY_ABILITY_TEMPLATE_ROOT / "build-profile.json5").read_text(encoding="utf-8"))
        main_pages = json.loads(
            (EMPTY_ABILITY_TEMPLATE_ROOT / "entry" / "src" / "main" / "resources" / "base" / "profile" / "main_pages.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(app_json["app"]["bundleName"], "com.example.emptyability")
        self.assertEqual(app_json["app"]["icon"], "$media:app_icon")
        self.assertEqual(module_json["module"]["name"], "entry")
        self.assertEqual(module_json["module"]["mainElement"], "EntryAbility")
        self.assertEqual(module_json["module"]["abilities"][0]["srcEntry"], "./ets/entryability/EntryAbility.ets")
        self.assertEqual(module_json["module"]["abilities"][0]["icon"], "$media:app_icon")
        self.assertEqual(module_json["module"]["abilities"][0]["startWindowIcon"], "$media:app_icon")
        self.assertEqual(main_pages["src"], ["pages/Index"])
        self.assertEqual(build_profile["app"]["products"][0]["compatibleSdkVersion"], "5.0.0(12)")
        self.assertEqual(build_profile["app"]["products"][0]["targetSdkVersion"], "5.0.0(12)")
        self.assertEqual(build_profile["app"]["products"][0]["runtimeOS"], "HarmonyOS")
        self.assertEqual(build_profile["app"]["signingConfigs"], [])

        index_text = (EMPTY_ABILITY_TEMPLATE_ROOT / "entry" / "src" / "main" / "ets" / "pages" / "Index.ets").read_text(
            encoding="utf-8"
        )
        smoke_counter_text = (
            EMPTY_ABILITY_TEMPLATE_ROOT / "entry" / "src" / "main" / "ets" / "components" / "SmokeCounter.ets"
        ).read_text(encoding="utf-8")
        self.assertIn("import { SmokeCounter } from '../components/SmokeCounter';", index_text)
        self.assertIn("SmokeCounter()", index_text)
        self.assertNotIn("@State", index_text)
        self.assertIn("export struct SmokeCounter", smoke_counter_text)
        self.assertIn("@State message: string = 'Harmony Smoke Ready';", smoke_counter_text)
        self.assertIn(".id('smoke-increment')", smoke_counter_text)

        for path in EMPTY_ABILITY_TEMPLATE_ROOT.rglob("*"):
            if path.is_file():
                if path.suffix == ".png":
                    continue
                text = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(EMPTY_ABILITY_TEMPLATE_ROOT).as_posix()):
                    self.assertNotIn("${", text)
                    self.assertNotIn("/Users/", text)
                    self.assertNotIn("certpath", text)
                    self.assertNotIn("storePassword", text)
                    self.assertNotIn("keyPassword", text)

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.minimal_scaffold_text)
                self.assertIn(fragment, self.readme_text)
                self.assertIn(fragment, self.readme_en_text)
                self.assertIn(fragment, self.skill_text)

        self.assertIn("页面入口与 smoke 组件解耦", self.minimal_scaffold_text)
        self.assertIn("页面入口与 smoke 组件解耦", self.readme_text)
        self.assertIn("The route page and smoke component are decoupled", self.readme_en_text)
        self.assertIn("Route/component split", self.skill_text)

    def test_sync_release_version_updates_skill_and_readmes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            (temp_root / "harmony-next").mkdir()
            shutil.copy2(SKILL_PATH, temp_root / "harmony-next" / "SKILL.md")
            shutil.copy2(README_PATH, temp_root / "README.md")
            shutil.copy2(README_EN_PATH, temp_root / "README_en.md")

            bare_version, tag_version = sync_release_version.sync_release_version(temp_root, "v9.8.7")

            self.assertEqual(bare_version, "9.8.7")
            self.assertEqual(tag_version, "v9.8.7")
            self.assertIn('version: "9.8.7"', (temp_root / "harmony-next" / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("Current local skill version: `v9.8.7`.", (temp_root / "harmony-next" / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("<!-- version: 9.8.7 -->", (temp_root / "harmony-next" / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("release-v9.8.7-1f6feb", (temp_root / "README.md").read_text(encoding="utf-8"))
            self.assertIn("releases/tag/v9.8.7", (temp_root / "README_en.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
