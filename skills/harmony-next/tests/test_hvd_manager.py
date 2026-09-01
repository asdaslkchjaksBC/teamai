from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hvd_manager.py"
SPEC = importlib.util.spec_from_file_location("hvd_manager", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class HvdManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "deployed"
        self.root.mkdir()
        self.source_dir = self.root / "Source Phone"
        self.source_dir.mkdir()
        (self.source_dir / "config.ini").write_text(
            "\n".join(
                [
                    "name=Source Phone",
                    "deviceType=phone",
                    "productModel=Source Phone",
                    "uuid=source-uuid",
                    f"instancePath={self.source_dir}",
                    "os.apiVersion=22",
                    "hw.hdc.port=notset",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.source_dir / "hardware-qemu.ini").write_text(
            "\n".join(
                [
                    "[General]",
                    "hvd.id=Source Phone",
                    "hvd.name=Source Phone",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.source_dir / "userdata.img.qcow2").write_text("disk", encoding="utf-8")
        (self.source_dir / "Log").mkdir()
        (self.source_dir / "Log" / "Emulator.log").write_text("old log", encoding="utf-8")
        (self.root / "Source Phone.ini").write_text(
            f"hvd.ini.encoding=UTF-8\npath={self.source_dir}\n",
            encoding="utf-8",
        )
        (self.root / "lists.json").write_text(
            json.dumps(
                [
                    {
                        "name": "Source Phone",
                        "productModel": "Source Phone",
                        "uuid": "source-uuid",
                        "instancePath": str(self.source_dir),
                    }
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_list_hvds_reads_registered_instances(self) -> None:
        hvds = MODULE.list_hvds(self.root)

        self.assertEqual(len(hvds), 1)
        self.assertEqual(hvds[0].name, "Source Phone")
        self.assertEqual(hvds[0].device_type, "phone")
        self.assertEqual(hvds[0].api_version, "22")
        self.assertEqual(hvds[0].path, self.source_dir)

    def test_list_command_accepts_json_after_subcommand(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--root", str(self.root), "list", "--json"],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["name"], "Source Phone")
        self.assertNotIn("uuid", payload[0])

    def test_list_command_uses_env_root_when_root_is_omitted(self) -> None:
        env = {**os.environ, "HARMONY_HVD_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "list", "--json"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["name"], "Source Phone")

    def test_doctor_reports_environment_probes(self) -> None:
        emulator = Path(self.temp_dir.name) / "Emulator"
        emulator.write_text("#!/bin/sh\necho HarmonyOS Emulator 9.9.9\n", encoding="utf-8")
        emulator.chmod(0o755)
        sdk_root = Path(self.temp_dir.name) / "sdk"
        sdk_root.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--root",
                str(self.root),
                "--emulator",
                str(emulator),
                "--sdk-root",
                str(sdk_root),
                "doctor",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["hvdRoot"]["path"], str(self.root.resolve()))
        self.assertEqual(payload["emulator"]["path"], str(emulator.resolve()))
        self.assertTrue(payload["emulator"]["executable"])
        self.assertEqual(payload["sdkRoot"]["path"], str(sdk_root.resolve()))
        self.assertEqual(payload["hvdCount"], 1)
        self.assertIn("HarmonyOS Emulator 9.9.9", payload["emulatorVersion"]["output"])
        self.assertNotIn("uuid", payload["hvds"][0])

    def test_create_hvd_clones_source_and_refreshes_identity(self) -> None:
        created = MODULE.create_hvd(
            root=self.root,
            source_name="Source Phone",
            new_name="CLI Phone",
            hdc_port=10123,
            include_logs=False,
        )

        self.assertEqual(created.name, "CLI Phone")
        self.assertTrue((self.root / "CLI Phone.ini").is_file())
        self.assertTrue((self.root / "CLI Phone" / "config.ini").is_file())
        self.assertTrue((self.root / "CLI Phone" / "userdata.img.qcow2").is_file())
        self.assertFalse((self.root / "CLI Phone" / "Log" / "Emulator.log").exists())

        root_ini = MODULE.read_ini(self.root / "CLI Phone.ini")
        config = MODULE.read_ini(self.root / "CLI Phone" / "config.ini")
        hardware = MODULE.read_sectionless_ini(self.root / "CLI Phone" / "hardware-qemu.ini")
        lists = json.loads((self.root / "lists.json").read_text(encoding="utf-8"))

        expected_path = str((self.root / "CLI Phone").resolve())
        self.assertEqual(root_ini["path"], expected_path)
        self.assertEqual(config["name"], "CLI Phone")
        self.assertEqual(config["productModel"], "CLI Phone")
        self.assertEqual(config["instancePath"], expected_path)
        self.assertEqual(config["hw.hdc.port"], "10123")
        self.assertNotEqual(config["uuid"], "source-uuid")
        self.assertEqual(hardware["hvd.id"], "CLI Phone")
        self.assertEqual(hardware["hvd.name"], "CLI Phone")
        self.assertIn("CLI Phone", {item["name"] for item in lists})

    def test_create_hvd_refuses_duplicate_names(self) -> None:
        with self.assertRaises(MODULE.HvdManagerError):
            MODULE.create_hvd(
                root=self.root,
                source_name="Source Phone",
                new_name="Source Phone",
                hdc_port=None,
                include_logs=False,
            )

    def test_delete_hvd_requires_exact_confirmation(self) -> None:
        MODULE.create_hvd(
            root=self.root,
            source_name="Source Phone",
            new_name="CLI Phone",
            hdc_port=None,
            include_logs=False,
        )

        with self.assertRaises(MODULE.HvdManagerError):
            MODULE.delete_hvd(self.root, "CLI Phone", confirm_name="wrong")

        deleted = MODULE.delete_hvd(self.root, "CLI Phone", confirm_name="CLI Phone")

        self.assertEqual(deleted.name, "CLI Phone")
        self.assertFalse((self.root / "CLI Phone.ini").exists())
        self.assertFalse((self.root / "CLI Phone").exists())
        lists = json.loads((self.root / "lists.json").read_text(encoding="utf-8"))
        self.assertNotIn("CLI Phone", {item["name"] for item in lists})

    def test_delete_hvd_refuses_path_outside_root(self) -> None:
        outside_dir = Path(self.temp_dir.name) / "outside-hvd"
        outside_dir.mkdir()
        (outside_dir / "config.ini").write_text(
            "\n".join(
                [
                    "name=Outside Phone",
                    "deviceType=phone",
                    "os.apiVersion=22",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.root / "Outside Phone.ini").write_text(
            f"hvd.ini.encoding=UTF-8\npath={outside_dir}\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(MODULE.HvdManagerError, "outside HVD root"):
            MODULE.delete_hvd(self.root, "Outside Phone", confirm_name="Outside Phone")

        self.assertTrue((self.root / "Outside Phone.ini").exists())
        self.assertTrue(outside_dir.exists())

    def test_download_image_command_reports_blocked(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "download-image",
                "--device-type",
                "phone",
                "--api-version",
                "22",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "blocked")
        self.assertEqual(payload["operation"], "image.download")

    def test_launch_preflight_blocks_without_trace_helper(self) -> None:
        emulator = Path(self.temp_dir.name) / "Emulator"
        emulator.write_text("#!/bin/sh\necho should-not-run\n", encoding="utf-8")
        emulator.chmod(0o755)
        sdk_root = Path(self.temp_dir.name) / "sdk"
        sdk_root.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--root",
                str(self.root),
                "--emulator",
                str(emulator),
                "--sdk-root",
                str(sdk_root),
                "launch-preflight",
                "--name",
                "Source Phone",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "blocked")
        self.assertEqual(payload["operation"], "emulator.launch.preflight")
        self.assertIn("traceName", payload["missingConfig"])
        self.assertIn("tracePipeHelper", payload["missingConfig"])
        self.assertIn("请在DevEco Studio中登录华为账号", payload["knownSymptom"])
        self.assertNotIn("emulatorCommand", payload)

    def test_launch_preflight_blocks_when_hvd_directory_is_missing(self) -> None:
        emulator = Path(self.temp_dir.name) / "Emulator"
        emulator.write_text("#!/bin/sh\necho should-not-run\n", encoding="utf-8")
        emulator.chmod(0o755)
        sdk_root = Path(self.temp_dir.name) / "sdk"
        sdk_root.mkdir()
        ready_file = Path(self.temp_dir.name) / "trace.ready"
        ready_file.write_text("ready\n", encoding="utf-8")
        shutil.rmtree(self.source_dir)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--root",
                str(self.root),
                "--emulator",
                str(emulator),
                "--sdk-root",
                str(sdk_root),
                "launch-preflight",
                "--name",
                "Source Phone",
                "--trace-name",
                "ai-emu-test",
                "--trace-helper-ready-file",
                str(ready_file),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "blocked")
        self.assertIn("hvdDirectory", payload["missingConfig"])
        self.assertNotIn("emulatorCommand", payload)

    def test_launch_preflight_outputs_trace_guarded_command(self) -> None:
        emulator = Path(self.temp_dir.name) / "Emulator"
        emulator.write_text("#!/bin/sh\necho should-not-run\n", encoding="utf-8")
        emulator.chmod(0o755)
        sdk_root = Path(self.temp_dir.name) / "sdk"
        sdk_root.mkdir()
        ready_file = Path(self.temp_dir.name) / "trace.ready"
        ready_file.write_text("ready\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--root",
                str(self.root),
                "--emulator",
                str(emulator),
                "--sdk-root",
                str(sdk_root),
                "launch-preflight",
                "--name",
                "Source Phone",
                "--trace-name",
                "ai-emu-test",
                "--trace-helper-ready-file",
                str(ready_file),
                "--hdc-port",
                "10123",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "allowed")
        self.assertEqual(payload["operation"], "emulator.launch.preflight")
        self.assertEqual(payload["traceName"], "ai-emu-test")
        self.assertEqual(payload["emulatorCommand"][0], str(emulator.resolve()))
        self.assertIn("-t", payload["emulatorCommand"])
        self.assertIn("ai-emu-test", payload["emulatorCommand"])
        self.assertIn("-hdcport", payload["emulatorCommand"])
        self.assertIn("10123", payload["emulatorCommand"])

    def test_launch_creates_trace_socket_and_starts_emulator(self) -> None:
        emulator = Path(self.temp_dir.name) / "Emulator"
        emulator.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import socket
                import sys

                trace_name = sys.argv[sys.argv.index("-t") + 1]
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.connect(f"/tmp/{trace_name}")
                client.sendall(b'{"event":"fake-start"}\\n')
                client.close()
                """
            ),
            encoding="utf-8",
        )
        emulator.chmod(0o755)
        image_root = Path(self.temp_dir.name) / "image-root"
        image_root.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--root",
                str(self.root),
                "--emulator",
                str(emulator),
                "launch",
                "--name",
                "Source Phone",
                "--image-root",
                str(image_root),
                "--trace-name",
                "ai-emu-test-launch",
                "--no-wait-target",
                "--timeout",
                "3",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "allowed")
        self.assertEqual(payload["operation"], "emulator.launch")
        self.assertEqual(payload["result"], "started")
        self.assertEqual(payload["traceName"], "ai-emu-test-launch")
        self.assertTrue(payload["socketConnected"])
        self.assertGreater(payload["traceBytesRead"], 0)
        self.assertIn("-t", payload["emulatorCommand"])
        self.assertIn("ai-emu-test-launch", payload["emulatorCommand"])


if __name__ == "__main__":
    unittest.main()
