import os.path
import json
from jsonschema import validate, Draft7Validator

def assert_valid_schema(data):
    # checks whether the given data matches the schema

    #TODO: get these from redis or similar - only get from disk first time

    schema = _load_json_schema('schemas/fotos.json')

    return validate(data, schema, format_checker=Draft7Validator.FORMAT_CHECKER)


def _load_json_schema(filename):
    # loads the given schema file
    filepath = os.path.join(os.path.dirname(__file__), filename)

    with open(filepath) as schema_file:
        return json.loads(schema_file.read())
