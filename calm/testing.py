"""
This is the testing module for Calm applications.

This defines a handy subclass with its utilities, so that you can use them to
test your Calm applications more conveniently and with less code.
"""
import json

from tornado.testing import AsyncHTTPTestCase

from calm.codec import CalmJSONDecoder, CalmJSONEncoder
from calm.core import CalmApp


class CalmTestCase(AsyncHTTPTestCase):
    """
    This is the base class to inherit in order to test your Calm app.
    """
    def get_calm_app(self):
        """
        This method needs to be implemented by the user.

        Simply return an instance of your Calm application so that Calm will
        know what are you testing.
        """
        pass  # pragma: no cover

    def get_app(self):
        """This one is for Tornado, returns the app under test."""
        calm_app = self.get_calm_app()

        if calm_app is None or not isinstance(calm_app, CalmApp):
            raise NotImplementedError(  # pragma: no cover
                "Please implement CalmTestCase.get_calm_app()"
            )

        return calm_app.make_app()

    def _request(self, url, *args,
                 expected_code=200,
                 expected_body=None,
                 expected_result=None,
                 expected_json_body=None,
                 query_args=None,
                 json_body=None,
                 **kwargs):
        """
        Makes a request to the `url` of the app and makes assertions.
        """
        if expected_result:
            # use expected_json_body further on
            expected_json_body = {
                self.get_calm_app().config['plain_result_key']: expected_result
            }

        # generate the query fragment of the URL
        if query_args is None:
            query_string = ''
        else:
            query_args_kv = ['='.join(
                [k, str(v)]
            ) for k, v in query_args.items()]
            query_string = '&'.join(query_args_kv)
        if query_string:
            url = url + '?' + query_string

        if ((kwargs.get('body') or json_body) and
                kwargs['method'] not in ('POST', 'PUT')):
            raise Exception(  # pragma: no cover
                "Cannot send body with methods other than POST and PUT"
            )

        if not kwargs.get('body'):
            if kwargs['method'] in ('POST', 'PUT'):
                if json_body:
                    kwargs['body'] = json.dumps(json_body, cls=CalmJSONEncoder)
                else:
                    kwargs['body'] = '{}'

        resp = self.fetch(url, *args, **kwargs)

        actual_code = resp.code
        self.assertEqual(actual_code, expected_code)

        if expected_body:
            self.assertEqual(resp.body.decode('utf-8'),
                             expected_body)  # pragma: no cover

        if expected_json_body:
            actual_json_body = json.loads(resp.body.decode('utf-8'),
                                          cls=CalmJSONDecoder)
            self.assertEqual(expected_json_body, actual_json_body)

        return resp

    def get(self, url, *args, **kwargs):
        """Makes a `GET` request to the `url` of your app."""
        kwargs.update(method='GET')
        return self._request(url, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        """Makes a `POST` request to the `url` of your app."""
        kwargs.update(method='POST')
        return self._request(url, *args, **kwargs)

    def put(self, url, *args, **kwargs):
        """Makes a `PUT` request to the `url` of your app."""
        kwargs.update(method='PUT')
        return self._request(url, *args, **kwargs)

    def delete(self, url, *args, **kwargs):
        """Makes a `DELETE` request to the `url` of your app."""
        kwargs.update(method='DELETE')
        return self._request(url, *args, **kwargs)
