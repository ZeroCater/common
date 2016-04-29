import json

from django.test import TestCase
from rest_framework.test import APITestCase


class ResponseTestCase(APITestCase):
    SUCCESS_HIGH_LEVEL_KEYS = ["data", "meta", "links"]
    SUCCESS_DATA_KEYS = ["id", "type", "attributes"]

    FAILURE_HIGH_LEVEL_KEYS = ["errors"]
    FAILURE_DATA_KEYS = ["status", "source", "detail"]

    def success_response_structure_test(self, response, status, relationship_keys=None):
        self.assertEqual(response.status_code, status)

        response_content = self.load_json(response)

        self.assertTrue(all(key in response_content for key in self.SUCCESS_HIGH_LEVEL_KEYS))

        for data in response_content["data"]:
            self.assertTrue(all(key in data for key in self.SUCCESS_DATA_KEYS))

            if relationship_keys:
                self.assertTrue("relationships" in data)
                relationships = data["relationships"]
                self.assertTrue(all(key in relationships for key in ["dietaryRestrictions", "dishVariations"]))

                for relationship_name, relationship in relationships.iteritems():
                    self.assertTrue(all(key in relationship for key in ["data", "meta"]))

                    for relationship_data in relationship["data"]:
                        self.assertTrue(all(key in relationship_data for key in ["type", "id"]))

    def failure_response_structure_test(self, response, status):
        self.assertEqual(response.status_code, status)

        response_content = self.load_json(response)

        self.assertTrue(all(key in response_content for key in self.FAILURE_HIGH_LEVEL_KEYS))

        for error in response_content["errors"]:
            self.assertTrue(all(key in error for key in self.FAILURE_DATA_KEYS))

    def load_json(self, response):
        return json.loads(response.content.decode())
