# app/tests/test_api.py
from mock import patch
from .fixtures import addTestCountries, addTestAddresses, getPublicID
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
from app.models import Country, Address
from app.config import TestConfig

from flask import current_app 
from flask_testing import TestCase as FlaskTestCase

from sqlalchemy.exc import DataError

###############################################################################
####                      flask test case instance                         ####
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
####                               tests                                   ####
###############################################################################

    def test_for_testdb(self):
        self.assertTrue('poptape_address_test' in 
                        self.app.config['SQLALCHEMY_DATABASE_URI'])

# -----------------------------------------------------------------------------

    def test_status_ok(self):
        headers = { 'Content-type': 'application/json' }
        response = self.client.get('/address/status', headers=headers)
        self.assertEqual(response.status_code, 200)

# -----------------------------------------------------------------------------

    def test_404(self):
        # this behaviour is slightly different to live as we've mocked the 
        headers = { 'Content-type': 'application/json' }
        response = self.client.get('/address/resourcenotfound', headers=headers)
        self.assertEqual(response.status_code, 404)

# -----------------------------------------------------------------------------

    def test_api_rejects_html_input(self):
        headers = { 'Content-type': 'text/html' }
        response = self.client.get('/address/status', headers=headers)
        self.assertEqual(response.status_code, 400)

# -----------------------------------------------------------------------------

    def test_country_model_saves_ok(self):
        country = Country(name = "United Kingdom",
                          iso_code = "GBR")
        db.session.add(country)
        db.session.commit()
        self.assertEqual(country.id, 1)

# -----------------------------------------------------------------------------

    def test_country_model_fails_iso_length(self):
        country = Country(name = "United Kingdom",
                          iso_code = "TOOLONG")
        try:
            db.session.add(country)
            db.session.commit()
        except DataError as error:
            db.session.rollback()
            self.assertTrue('value too long' in str(error))

# -----------------------------------------------------------------------------

    def test_return_list_of_countries(self):
        countries = addTestCountries() 
        headers = { 'Content-type': 'application/json' }
        response = self.client.get('/address/countries', headers=headers)
        results = response.json
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results.get('countries')), 4)

# -----------------------------------------------------------------------------

    def test_api_rejects_unauthenticated_get(self):
        headers = { 'Content-type': 'application/json' }
        response = self.client.get('/address', headers=headers)
        self.assertEqual(response.status_code, 401)

# -----------------------------------------------------------------------------

    def test_one_address_ok(self):
        addresses = addTestAddresses()
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        url = '/address/'+addresses[0].address_id
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, 200)

# -----------------------------------------------------------------------------

    def test_list_of_addresses_ok(self):
        addresses = addTestAddresses()
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        response = self.client.get('/address', headers=headers)
        self.assertEqual(response.status_code, 200)
        # expect the number of returned addresses to be 3 as we are filtering by public_id
        results = response.json
        self.assertEqual(len(results.get('addresses')), 3)
        # get the retuned address with country name of Brazil and check the returned data matches
        original_brazil_address = None
        for addy in addresses:
            if addy.country_id == 3:
                original_brazil_address = addy

        returned_brazil_address = None
        for returned_addy in results['addresses']:
            if returned_addy.get('country') == "Brazil":
                returned_brazil_address = returned_addy

        self.assertEqual(original_brazil_address.post_zip_code, returned_brazil_address.get('post_zip_code'))

# -----------------------------------------------------------------------------

    def test_all_addresses_admin_incl_paging(self):
        addresses = addTestAddresses()
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        response = self.client.get('/address/admin/address', headers=headers)
        self.assertEqual(response.status_code, 200)
        results = response.json
        # test total number of records and limit per page equals config
        add_limit_per_page = int(TestConfig.ADDRESS_LIMIT_PER_PAGE)
        self.assertEqual(len(results.get('addresses')), add_limit_per_page)
        self.assertEqual(results.get('total_records'), 6)

# -----------------------------------------------------------------------------

    def test_rate_limiting(self):
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        response1 = self.client.get('/address/admin/ratelimited', headers=headers)
        self.assertEqual(response1.status_code, 429)

# -----------------------------------------------------------------------------

    def test_delete_ok(self):
        addresses = addTestAddresses()
        a_valid_address_id = addresses[0].address_id # valid address for this user
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        # this address is valid for this user so should delete ok. we also have a check in the delete
        # itself - we delete on address_id AND public_id
        url = '/address/'+a_valid_address_id
        response = self.client.delete(url, headers=headers)
        self.assertEqual(response.status_code, 204) # successful delete with no message

# -----------------------------------------------------------------------------

    def test_delete_fail(self):
        addresses = addTestAddresses()
        invalid_address_id = addresses[1].address_id # invalid address for this user
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        # this address is invalid for this user so should not delete 
        url = '/address/'+invalid_address_id
        response = self.client.delete(url, headers=headers)
        self.assertEqual(response.status_code, 401)

# -----------------------------------------------------------------------------

    def test_create_ok(self):
        countries = addTestCountries()
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        create_json = { 'public_id': getPublicID(),
                        'house_name': 'The Larches',
                        'house_number': '12', # house nos are a string because of nos. like 12A
                        'address_line_1': 'Green Lane',
                        'address_line_2': 'Little Bowden',
                        'address_line_3': 'Market Harborough',
                        'state_region_county': 'Leicestershire',
                        'iso_code': 'GBR',
                        'post_zip_code': 'LE13 5WI' }

        response = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response.status_code, 201)
        rep_body = response.json
        address_id = rep_body.get('address_id')

        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        url = '/address/'+address_id
        check_response = self.client.get(url, headers=headers)
        check_body = check_response.json
        self.assertEqual(check_response.status_code, 200)
        #self.assertEqual(address_id, check_body.get('address_id'))
        #self.assertEqual(create_json.get('public_id'), check_body.get('public_id'))
        self.assertEqual(create_json.get('house_name'), check_body.get('house_name'))
        self.assertEqual(create_json.get('house_number'), check_body.get('house_number'))
        self.assertEqual(create_json.get('address_line_1'), check_body.get('address_line_1'))
        self.assertEqual(create_json.get('address_line_2'), check_body.get('address_line_2'))
        self.assertEqual(create_json.get('address_line_3'), check_body.get('address_line_3'))
        self.assertEqual(create_json.get('state_region_county'), check_body.get('state_region_county'))
        self.assertEqual(create_json.get('post_zip_code'), check_body.get('post_zip_code'))
        self.assertEqual('United Kingdom', check_body.get('country'))

# -----------------------------------------------------------------------------

    def test_fail_with_bad_iso(self):
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        create_json = { 'public_id': getPublicID(),
                        'house_name': 'The Larches',
                        'house_number': '12', # house nos are a string because of nos. like 12A
                        'address_line_1': 'Green Lane',
                        'address_line_2': 'Little Bowden',
                        'address_line_3': 'Market Harborough',
                        'state_region_county': 'Leicestershire',
                        'iso_code': 'ZZZ',
                        'post_zip_code': 'LE13 5WI' }

        response = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response.status_code, 400)

# -----------------------------------------------------------------------------

    def test_fail_with_extra_field_in_post(self):
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        create_json = { 'public_id': getPublicID(),
                        'house_name': 'The Larches',
                        'house_number': '12', # house nos are a string because of nos. like 12A
                        'address_line_1': 'Green Lane',
                        'address_line_2': 'Little Bowden',
                        'address_line_3': 'Market Harborough',
                        'address_line_4': 'Extra Address Line',
                        'state_region_county': 'Leicestershire',
                        'iso_code': 'GBR',
                        'post_zip_code': 'LE13 5WI' }

        response = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response.status_code, 400)

# -----------------------------------------------------------------------------

    def test_various_postcodes(self):
        countries = addTestCountries()
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        create_json = { 'public_id': getPublicID(),
                        'house_name': 'The Larches',
                        'house_number': '12', # house nos are a string because of nos. like 12A
                        'address_line_1': 'Green Lane',
                        'address_line_2': 'Little Bowden',
                        'address_line_3': 'Market Harborough',
                        'state_region_county': 'Leicestershire',
                        'iso_code': 'GBR',
                        'post_zip_code': '4LE5464 5£@£WI' }

        response1 = self.client.post('/address', json=create_json, headers=headers)
        print(response1.json)
        self.assertEqual(response1.status_code, 400)

        create_json['post_zip_code'] = 'X999342'
        response2 = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response2.status_code, 400)        
        
        create_json['post_zip_code'] = 'DE21 5EA'
        response3 = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response3.status_code, 201)

        create_json['post_zip_code'] = 'DE215EA'
        response4 = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response4.status_code, 201)        

        create_json['post_zip_code'] = '1234567890'
        response5 = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response5.status_code, 400)

        create_json['post_zip_code'] = ''
        response6 = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response6.status_code, 400)        

        del create_json['post_zip_code']
        response7 = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response7.status_code, 400)

# -----------------------------------------------------------------------------

    def test_fail_with_missing_house_name_and_number(self):
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        create_json = { 'public_id': getPublicID(),
                        'address_line_1': 'Green Lane',
                        'address_line_2': 'Little Bowden',
                        'address_line_3': 'Market Harborough',
                        'state_region_county': 'Leicestershire',
                        'iso_code': 'GBR',
                        'post_zip_code': 'LE13 5WI' }

        response = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response.status_code, 400)

# -----------------------------------------------------------------------------

    def test_non_uk_json_schema(self):
        countries = addTestCountries()
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        create_json = { 'public_id': getPublicID(),
                        'house_name': 'The Larches',
                        'house_number': '12', # house nos are a string because of nos. like 12A
                        'address_line_1': 'Green Lane',
                        'address_line_2': 'Little Bowden',
                        'address_line_3': 'Market Harborough',
                        'state_region_county': 'Leicestershire',
                        'iso_code': 'FRA',
                        'post_zip_code': 'LE13 5WI' }

        response = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response.status_code, 201)

# -----------------------------------------------------------------------------

    def test_no_iso_code(self):
        countries = addTestCountries()
        headers = { 'Content-type': 'application/json', 'x-access-token': 'somefaketoken' }
        create_json = { 'public_id': getPublicID(),
                        'house_name': 'The Larches',
                        'house_number': '12', # house nos are a string because of nos. like 12A
                        'address_line_1': 'Green Lane',
                        'address_line_2': 'Little Bowden',
                        'address_line_3': 'Market Harborough',
                        'state_region_county': 'Leicestershire',
                        'post_zip_code': 'LE13 5WI' }

        response = self.client.post('/address', json=create_json, headers=headers)
        self.assertEqual(response.status_code, 400)
