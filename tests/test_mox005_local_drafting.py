import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from moxie.first_slice import ContractError
from moxie.local_drafter import draft_with_ollama
from moxie.operator_service import OperatorService
from test_operator_service import example


class Response(io.BytesIO):
    status = 200


class MOX005Tests(unittest.TestCase):
    def test_local_request_is_bounded_and_returns_only_draft(self):
        with patch("moxie.local_drafter.urlopen", return_value=Response(b'{"response":"Editable draft"}')) as call:
            value = draft_with_ollama("Gardening", "Beginners", (("e1", "Soil matters"),))
        self.assertEqual(value, "Editable draft")
        request = call.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "qwen2.5:7b-instruct")
        self.assertEqual(payload["options"]["num_predict"], 280)
        self.assertEqual(call.call_args.kwargs["timeout"], 65)
        self.assertTrue(request.full_url.startswith("http://127.0.0.1:"))

    def test_bad_model_or_missing_evidence_fails_closed(self):
        with self.assertRaises(ContractError):
            draft_with_ollama("Gardening", "Beginners", ())
        with self.assertRaises(ContractError):
            draft_with_ollama("Gardening", "Beginners", (("e1", "noted"),), model="remote")

    def test_completed_history_joins_review_and_approved_brief(self):
        with tempfile.TemporaryDirectory() as root:
            service = OperatorService(Path(root))
            item = service.submit(example()).approval_item
            service.review(item.item_id, "approved", "Ariel", "Reviewed")
            records = OperatorService(Path(root)).reviewed()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["reviewer"], "Ariel")
            self.assertEqual(records[0]["brief"].title, "Garden planning")


if __name__ == "__main__":
    unittest.main()
