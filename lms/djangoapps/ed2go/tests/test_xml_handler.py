from xml.etree import ElementTree

from django.test import TestCase

from ed2go.xml_handler import XMLHandler


class XMLHandlerTests(TestCase):
    def setUp(self):
        self.xmlh = XMLHandler()

    def test_xml_from_dict(self):
        """Correctly convert a dictionary to XML."""
        data = {
            'root': {
                'key': 'value'
            }
        }
        expected = '<root xmlns="https://api.ed2go.com"><key>value</key></root>'
        self.assertEqual(self.xmlh.xml_from_dict(data), expected)

    def test_clean_tag(self):
        """Extracts the element tag."""
        element = '{https://api.ed2go.com}TestElement'
        expected = 'TestElement'
        self.assertEqual(self.xmlh.clean_tag(element), expected)

    def test_dict_from_xml(self):
        """Correctly converts an XML element to a dict."""
        xml_tree = ElementTree.fromstring('<root><key>value</key></root>')
        expected = {'key': 'value'}
        self.assertEqual(self.xmlh.dict_from_xml(xml_tree), expected)

    def test_registration_response_data_from_xml(self):
        """Correctly converts registration request response XML to a dictionary."""
        expected = {'TestUser': 'tester'}
        test_response_xml = '<?xml version="1.0" encoding="utf-8"?>' \
            '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">' \
            '<soap:Body>' \
            '<GetRegistrationResponse xmlns="https://api.ed2go.com">' \
            '<RegistrationsResponse>' \
            '<Registrations>' \
            '<Registration>' \
            '<TestUser>' + expected['TestUser'] + '</TestUser>' \
            '</Registration>' \
            '</Registrations>' \
            '</RegistrationsResponse>' \
            '</GetRegistrationResponse>' \
            '</soap:Body>' \
            '</soap:Envelope>'

        self.assertEqual(self.xmlh.registration_data_from_xml(test_response_xml), expected)

    def test_completion_response_data_from_xml(self):
        """Correctly converts completion report update request response XML to a dictionary."""
        expected = {'Success': 'true'}
        test_response_xml = '<?xml version="1.0" encoding="utf-8"?>' \
            '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">' \
            '<soap:Body>' \
            '<UpdateCompletionReportResponse xmlns="https://api.ed2go.com">' \
            '<Response>' \
            '<Result>' \
            '<Success>' + expected['Success'] + '</Success>' \
            '</Result>' \
            '</Response>' \
            '</UpdateCompletionReportResponse>' \
            '</soap:Body>' \
            '</soap:Envelope>'

        self.assertEqual(self.xmlh.completion_update_response_data_from_xml(test_response_xml), expected)
