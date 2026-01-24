import unittest
import json
from modules.ai_core import _clean_json_output

class TestAICore(unittest.TestCase):
    
    def test_clean_json_output_markdown(self):
        raw = "Here is the json:\n```json\n{\"key\": \"value\"}\n```"
        expected = "{\"key\": \"value\"}"
        self.assertEqual(_clean_json_output(raw), expected)

    def test_clean_json_output_plain(self):
        raw = "Some text\n[{\"id\": 1}]\nMore text"
        expected = "[{\"id\": 1}]"
        self.assertEqual(_clean_json_output(raw), expected)

    def test_clean_json_output_dict(self):
        raw = "Sure:\n{\"summary\": \"Test\"}"
        expected = "{\"summary\": \"Test\"}"
        self.assertEqual(_clean_json_output(raw), expected)

if __name__ == '__main__':
    unittest.main()
