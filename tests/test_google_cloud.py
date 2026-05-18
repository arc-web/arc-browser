import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from arc_browser.google_cloud import (
    api_ids_for_services,
    build_prepare_packet,
    classify_blocker,
    stable_urls,
)


class GoogleCloudRecipeTest(unittest.TestCase):
    def test_api_ids_for_services(self):
        self.assertEqual(
            api_ids_for_services(["search-console", "analytics", "gmail"]),
            [
                "searchconsole.googleapis.com",
                "analyticsdata.googleapis.com",
                "analytics.googleapis.com",
                "gmail.googleapis.com",
            ],
        )

    def test_stable_urls_include_project(self):
        urls = stable_urls("arc-test", ["gmail.googleapis.com"])
        self.assertIn("project=arc-test", urls["credentials"])
        self.assertEqual(
            urls["api_library"][0],
            "https://console.developers.google.com/apis/api/gmail.googleapis.com/overview?project=arc-test",
        )

    def test_prepare_packet_uses_project_selector_without_project(self):
        packet = build_prepare_packet(
            "mike.ensor@locafy.com",
            "gmail,analytics",
            "prompt",
            "",
            "google-cloud-mike-ensor-locafy-com",
        )
        self.assertEqual(packet["start_url"], packet["stable_urls"]["project_selector"])
        self.assertIn("download_confirmation", packet["handoff_reasons"])

    def test_blocker_classification(self):
        self.assertEqual(classify_blocker("https://accounts.google.com/signin", ""), "login")
        self.assertEqual(classify_blocker("https://console.cloud.google.com", "Enable billing to continue"), "billing")


if __name__ == "__main__":
    unittest.main()
