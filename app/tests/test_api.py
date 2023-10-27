# app/tests/test_api.py
from mock import patch
from functools import wraps
from flask import jsonify

# have to mock the require_access_level decorator here before it 
# gets attached to any classes or functions
def mock_dec(access_level,request):
    def actual_decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):

            token = request.headers.get('x-access-token')

            if not token:
                return jsonify({ 'message': 'Naughty one!'}), 401
            pub_id = getPublicID()
            return f(pub_id, request, *args, **kwargs)

        return decorated
    return actual_decorator

patch('app.decorators.require_access_level', mock_dec).start()

from app import create_app, db
from app.config import TestConfig

from flask_testing import TestCase as FlaskTestCase

from sqlalchemy.exc import DataError

###############################################################################
#                         flask test case instance                            #
###############################################################################

class MyTest(FlaskTestCase):

    ############################
    #### setup and teardown ####
    ############################

    def create_app(self):
        app = create_app(TestConfig)
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

###############################################################################
#                                  tests                                      #
###############################################################################

#    def test_for_testdb(self):
#        self.assertTrue('poptape_address_test' in
#                        self.app.config['SQLALCHEMY_DATABASE_URI'])

# -----------------------------------------------------------------------------

    def test_status_ok(self):
        headers = { 'Content-type': 'application/json' }
        response = self.client.get('/fotos/status', headers=headers)
        self.assertEqual(response.status_code, 200)

# -----------------------------------------------------------------------------

    def test_404(self):
        # this behaviour is slightly different to live as we've mocked the 
        headers = { 'Content-type': 'application/json' }
        response = self.client.get('/fotos/resourcenotfound', headers=headers)
        self.assertEqual(response.status_code, 404)

# -----------------------------------------------------------------------------

    def test_api_rejects_html_input(self):
        headers = { 'Content-type': 'text/html' }
        response = self.client.get('/fotos/status', headers=headers)
        self.assertEqual(response.status_code, 400)

# -----------------------------------------------------------------------------

