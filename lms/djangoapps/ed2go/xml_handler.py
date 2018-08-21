import re
from xml.etree import ElementTree


class XMLHandler(object):
    """Ed2go specific XML handler."""
    headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
    soap_wrapper = '<?xml version="1.0" encoding="utf-8"?>' \
        '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">' \
        '<soap12:Body>' \
        '{inner}' \
        '</soap12:Body>' \
        '</soap12:Envelope>'

    def xml_from_dict(self, data):
        """
        Construct an XML string that would go into the soap_wrapper inner content.

        Args:
            data (dict): Dictionary with the data that is suppose to be compiled into
                XML. The keys of the dictionary are XML element tags, values are values.
                NOTE: The dictionary has to start with ` 'key': {...} `, e.g.:
                    'root': {
                        'tag': 'value',
                        'tag2': 'value2',
                        ...
                    }
                because the root tag needs the `xmlns` attribute.

        Returns:
            XML formatted string from the input data.
        """
        xml = ''
        for k, v in data.items():  # pylint: disable=invalid-name
            elements = ''
            for sk, sv in v.items():  # pylint: disable=invalid-name
                elements += '<{key}>{value}</{key}>'.format(key=sk, value=sv)
            xml += '<{key} xmlns="https://api.ed2go.com">{elements}</{key}>'.format(
                key=k, elements=elements
            )
        return xml

    def request_data_from_dict(self, data):
        return self.soap_wrapper.format(inner=self.xml_from_dict(data))

    def request_data_from_xml(self, data):
        return self.soap_wrapper.format(inner=data)

    def clean_tag(self, element):
        """
        Remove the schema prefix.
        Example:
          "{https://api.ed2go.com}NewRegistration" > "NewRegistration"
        """
        return re.sub(r'{[\w\:\/\.]*}', '', element)

    def dict_from_xml(self, elements):
        """
        Construct a dictionary from the XML tree.

        Args:
            elements (list): List of XML elements that are compiled into a dictionary.

        Returns:
            A dictionary with key being the elements tags.
        """
        data = {}
        for element in elements:
            if element.getchildren():
                data[self.clean_tag(element.tag)] = self.dict_from_xml(element.getchildren())
            else:
                data[self.clean_tag(element.tag)] = element.text
        return data

    def _extract_elements_from_xml(self, xml, path):
        """
        Extract XML elements based on the given path.

        Args:
            xml (str): The whole SOAP XML envelope in string format.
            path (str): The XML path to the sequence with the requested elements.
                Example:
                    './soap:Body' \
                    '/a:GetRegistrationResponse' \
                    '/a:RegistrationsResponse' \
                    '/a:Registrations' \
                    '/a:Registration'

        Returns:
            List of sequences found in the passed in XML string.
        """
        tree = ElementTree.fromstring(xml)
        namespace = {
            'soap': 'http://www.w3.org/2003/05/soap-envelope',
            'a': 'https://api.ed2go.com'
        }
        return tree.findall(path, namespace)

    def registration_data_from_xml(self, xml):
        """
        Extract the registration XML elements from the XML tree.

        Args:
            xml (str): XML tree in string format (raw content from the GetRegistration endpoint.)

        Returns:
            A dictionary with all the registration information extracted from dict.
        """
        path = './soap:Body' \
               '/a:GetRegistrationResponse' \
               '/a:RegistrationsResponse' \
               '/a:Registrations' \
               '/a:Registration'
        elements = self._extract_elements_from_xml(xml, path)
        return self.dict_from_xml(elements[0])

    def completion_update_response_data_from_xml(self, xml):
        """
        Extract the completion update response XML elements from the XML tree.

        Args:
            xml (str): XML tree in string format (raw content from the GetRegistration endpoint.)

        Returns:
            A dictionary with all the response information extracted from dict:
                * Result:
                    - Success
                    - Code
                    - Message
        """
        path = './soap:Body' \
               '/a:UpdateCompletionReportResponse' \
               '/a:Response' \
               '/a:Result'
        elements = self._extract_elements_from_xml(xml, path)
        return self.dict_from_xml(elements[0])
