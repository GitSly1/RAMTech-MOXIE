import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from moxie.first_slice import ContractError
from moxie.local_drafter import draft_with_ollama
from moxie.operator_service import OperatorService
from test_operator_service import example
from test_mox005_local_drafting import Response


class MOX006Tests(unittest.TestCase):
    def test_versions_are_persistent_immutable_and_idempotent_for_same_content(self):
        with tempfile.TemporaryDirectory() as folder:
            service = OperatorService(Path(folder))
            service.save_draft(example(brief_body="First"))
            service.save_draft(example(brief_body="First"))
            service.save_draft(example(brief_body="Second"))
            records = OperatorService(Path(folder)).draft_versions("op-1")
            self.assertEqual([x["payload"]["brief_body"] for x in records], ["Second", "First"])
            self.assertEqual(OperatorService(Path(folder)).drafts()[0].brief_body, "Second")

    def test_selected_format_and_tone_reach_local_prompt(self):
        with patch("moxie.local_drafter.urlopen", return_value=Response(b'{"response":"Draft [ev-1]"}')) as call:
            draft_with_ollama("Garden", "Growers", (("ev-1", "Soil matters"),), content_format="Checklist", tone="Friendly")
        prompt = json.loads(call.call_args.args[0].data)["prompt"]
        self.assertIn("Format: Checklist", prompt)
        self.assertIn("Tone: Friendly", prompt)
        self.assertIn("[VERIFY]", prompt)

    def test_unknown_format_fails_before_model_request(self):
        with patch("moxie.local_drafter.urlopen") as call:
            with self.assertRaises(ContractError):
                draft_with_ollama("Garden", "Growers", (("ev-1", "notes"),), content_format="Other")
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
