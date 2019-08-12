# app/main/views.py
from app import mongo, limiter, flask_uuid
from flask import jsonify, request, abort, url_for
from flask import make_response, session
from flask import current_app as app
from app.main import bp
from app.models import Foto
from app.assertions import assert_valid_schema
from app.decorators import require_access_level

from jsonschema.exceptions import ValidationError as JsonValidationError

import boto3
from botocore.client import Config

import requests

import uuid
import datetime
import json

from pymongo import ASCENDING, DESCENDING
from pymongo import errors as PymongoException

#-----------------------------------------------------------------------------#
# fotos routes
#-----------------------------------------------------------------------------#

#-----------------------------------------------------------------------------#
# return items by logged in user - optional pagination with from and to fields
#-----------------------------------------------------------------------------#

@bp.route('/fotos', methods=['GET'])
@require_access_level(10, request)
def get_fotos_by_user(public_id, request):

    #TODO: change all this - currently not saving by public_id but by item_id

    offset, sort = 0, 'id_asc'
    limit = int(app.config['PAGE_LIMIT'])

    if 'offset' in request.args:
        offset = int(request.args['offset'])
    if 'limit' in request.args:
        limit = int(request.args['limit'])
    if 'sort' in request.args:
        sort = request.args['sort']

    starting_id = None
    try:
        starting_id = mongo.db[public_id].find().sort('_id', ASCENDING)
        #results_count = starting_id.count()
    except:
        jsonify({ 'message': 'There\'s a problem with your arguments or mongo or both or something else ;)'}), 400

    if starting_id is None:
        return jsonify({ 'message': 'Nowt here chap'}), 404

    if starting_id.count() <= offset:
        return jsonify({ 'message': 'offset is too big'}), 400

    if offset < 0:
        return jsonify({ 'message': 'offset is negative'}), 400

    last_id = starting_id[offset]['_id']
    results_count = starting_id.count()

    fotos = []
    try:
        fotos = mongo.db[public_id].find({'_id': { '$gte': last_id}}).sort('_id', ASCENDING).limit(limit)
    except:
        jsonify({ 'message': 'There\'s a problem with your arguments or planets are misaligned. try sacrificing a goat or something...'}), 400

    output = []
    for foto in fotos:
        foto['id'] = str(foto['_id'])
        del foto['_id']
        output.append(foto)
    url_offset_next = offset+limit
    url_offset_prev = offset-limit
    if url_offset_prev < 0:
         url_offset_prev = 0

    if url_offset_next > fotos.count():
        next_url = None

    return_data = { 'fotos': output }

    if url_offset_next < results_count:
        next_url = '/fotos?limit='+str(limit)+'&offset='+str(url_offset_next)+'&sort='+sort
        return_data['next_url'] = next_url

    if offset > 0:
        prev_url = '/fotos?limit='+str(limit)+'&offset='+str(url_offset_prev)+'&sort='+sort
        return_data['prev_url'] = prev_url

    return jsonify(return_data), 200


#-----------------------------------------------------------------------------#
# return list of fotos associated with an item 
#-----------------------------------------------------------------------------#

@bp.route('/fotos/item/<uuid:item_id>', methods=['GET'])
@require_access_level(10, request)
def return_all_items_listed(public_id, request, item_id):

    item_id = str(item_id)

    offset, sort = 0, 'id_asc'
    limit = int(app.config['PAGE_LIMIT'])

    if 'offset' in request.args:
        offset = int(request.args['offset'])
    if 'limit' in request.args:
        limit = int(request.args['limit'])
    if 'sort' in request.args:
        sort = request.args['sort']

    starting_id = None
    try:
        starting_id = mongo.db[item_id].find().sort('_id', ASCENDING)
        #results_count = starting_id.count()
    except:
        jsonify({ 'message': 'There\'s a problem with your arguments or mongo or both or something else ;)'}), 400

    if starting_id is None:
        return jsonify({ 'message': 'Nowt here chap'}), 404

    if starting_id.count() <= offset:
        return jsonify({ 'message': 'offset is too big'}), 400

    if offset < 0:
        return jsonify({ 'message': 'offset is negative'}), 400

    last_id = starting_id[offset]['_id']
    results_count = starting_id.count()

    fotos = []
    try:
        fotos = mongo.db[item_id].find({'_id': { '$gte': last_id}}).sort('_id', ASCENDING).limit(limit)
    except:
        jsonify({ 'message': 'There\'s a problem with your arguments or planets are misaligned. try sacrificing a goat or something...'}), 400

    output = []
    for foto in fotos:
        foto['id'] = str(foto['_id'])
        del foto['_id']
        output.append(foto)
    url_offset_next = offset+limit
    url_offset_prev = offset-limit
    if url_offset_prev < 0:
         url_offset_prev = 0

    if url_offset_next > fotos.count():
        next_url = None

    return_data = { 'fotos': output }

    if url_offset_next < results_count:
        next_url = '/fotos/'+item_id+'?limit='+str(limit)+'&offset='+str(url_offset_next)+'&sort='+sort
        return_data['next_url'] = next_url

    if offset > 0:
        prev_url = '/fotos/'+item_id+'?limit='+str(limit)+'&offset='+str(url_offset_prev)+'&sort='+sort
        return_data['prev_url'] = prev_url

    return jsonify(return_data), 200


#-----------------------------------------------------------------------------#
# create item by logged in user
#-----------------------------------------------------------------------------#

@bp.route('/fotos', methods=['POST'])
@require_access_level(10, request)
def create_foto(public_id, request):

    input_data = request.get_json()

    # validate input against json schemas
    try:
        assert_valid_schema(input_data)
    except JsonValidationError as err:
        return jsonify({ 'message': 'Check ya inputs mate.', 'error': err.message }), 400

#    new_item = Item(input_data['name'],
#                    input_data['description'],
#                    input_data['owner'],
#                    input_data['status'],
#                    input_data['item_type'])
#
#    app.logger.debug('[ITEM]: ' + new_item.owner)

    # each item has it's own collection that foto data is stored in
    foto_id = str(uuid.uuid4())
    item_id = input_data['item_id']
    del input_data['item_id']
    input_data['public_id'] = public_id
    try:
        mongo.db[item_id].insert_one({"_id" : foto_id, "metadata": input_data})    
    except PymongoException as e:
        message = { 'message': 'Ooopsy, couldn\'t create mongo document.' }
        app.logger.error("Pymongo error [%s]", str(e))
        if app.config['ENVIRONMENT'] != 'PRODUCTION':
            message['error'] = str(e)
        return jsonify(message), 500

    return jsonify({ 'foto_id': foto_id }), 201

# -----------------------------------------------------------------------------

@bp.route('/fotos/ctaws', methods=['GET'])
@require_access_level(10, request)
def connect_to_aws(public_id, request):

    collection_name = 'Z'+public_id.replace('-','')

    token = request.headers.get('x-access-token')
    #test_public_id = '9cbb22d6-1a31-470d-802f-a7766f1b87f5'

    # jobbob3
    test_public_id = '150ce7b2-fbb4-4a45-82d9-6c97b0886847' #'4d31db4b-cc6e-4e71-8a01-c1df8ad28088'
    collection_name = 'Z150ce7b2fbb44a4582d96c97b0886847'

    headers = { 'Content-Type': 'application/json', 'x-access-token': token }
    r = requests.get(app.config['CHECK_ACCESS_URL']+test_public_id+'/aws', headers=headers)    
    app.logger.debug('connect_to_aws Status Code: '+str(r.status_code))  
    app.logger.debug('connect_to_aws Return text: '+r.text)
    if r.status_code != 200:
        return jsonify({ 'message': 'Ooopsy, that\'s not supposed to happen' })

    returned_json = r.json()
    app.logger.debug('connect_to_aws  Returned JSON: '+str(returned_json)) 

    # setup aws
    iam = boto3.client("iam",
                       aws_access_key_id=returned_json['aws_AccessKeyId'],
                       aws_secret_access_key=returned_json['aws_SecretAccessKey'],
                       config=Config(signature_version='s3v4'))
                       #config=Config(use-sigv4 = True))
                       #aws_session_token=os.getenv('AWS_SESSION_TOKEN'))

    s3 = boto3.client("s3",
                      aws_access_key_id=returned_json['aws_AccessKeyId'],
                      aws_secret_access_key=returned_json['aws_SecretAccessKey'],
                      config=Config(signature_version='s3v4'))
                       #config=Config(use-sigv4 = True))

    app.logger.debug('connect_to_aws  Returned Objects:\n'+str(type(iam))+'\n'+str(type(s3))+'\n')
    
    app.logger.debug(s3.list_buckets())

    # for bucket in s3.buckets.all():
    buckets = s3.list_buckets()
    for bucket in buckets['Buckets']:
        app.logger.debug('Bucket name: '+bucket['Name'])

    #app.logger.debug(s3.list_buckets())

    kwargs = { 'Bucket': buckets['Buckets'][0]['Name'] }
    prefix = 'items/'+collection_name
    #prefix = None

    # If the prefix is a single string (not a tuple of strings), we can
    # do the filtering directly in the S3 API.
    if isinstance(prefix, str):
        kwargs['Prefix'] = prefix

    #kwargs['Key'] = 'items/Z9cbb22d61a31470d802fa7766f1b87f5/background_01.jpg'

    
    app.logger.debug('KWARGS!\n'+str(kwargs))
    # The S3 API response is a large blob of metadata.
    # 'Contents' contains information about the listed objects.
    resp = s3.list_objects(**kwargs)
    #resp = s3.get_object(**kwargs)

    app.logger.debug('RESP!\n'+str(resp))

    try:
        contents = resp['Contents']
    except KeyError:
        return

    for obj in contents:
        key = obj['Key']
        app.logger.debug('[][] key is : '+key)

    #resp = s3.list_objects_v2( Bucket='poptape.club' , Prefix='items/' )
    #resp = s3.list_objects_v2( Bucket='poptape.club' )
    #app.logger.debug(str(resp))

    return jsonify({ 'aws_json': returned_json, 'contents': contents })

#-----------------------------------------------------------------------------#
# return item by logged in user - pass in item_id
#-----------------------------------------------------------------------------#

@bp.route('/fotos/items/<item_id>', methods=['GET'])
@require_access_level(10, request)
def return_one_item(public_id, request, item_id):

    app.logger.debug('In /items/items/<item_id> (GET)')    
    #TODO: input validation

    record = _return_document(public_id, item_id)
 
    if isinstance(record,dict):
        return jsonify(record), 200

    collection_name = 'Z' + public_id.replace('-','')
    return jsonify({ 'message': 'Could not find the item ['+item_id+'] in collection ['+collection_name+']' }), 404


#-----------------------------------------------------------------------------#
# return items by passed in user public_id - returns all items - ADMIN only
#-----------------------------------------------------------------------------#

@bp.route('/fotos/items/user/<other_user_public_id>', methods=['GET'])
@require_access_level(5, request)
def return_items_of_public_id(public_id, request, other_user_public_id):

    collection_name = 'Z' + other_user_public_id.replace('-','')

    output = []
    try:    
        records = mongo.db[collection_name].find()
    except:
        return jsonify({ 'message': 'Something\'s up with the item store. Could not find the collection ['+collection_name+']' }), 500
    
    if records.count() == 0:
        return jsonify({ 'message': 'Could not find any items in collection ['+collection_name+']' }), 404

    for record in records:
        if isinstance(record['_id'], ObjectId):
            record['item_id'] = str(record['_id'])
            del record['_id']
        output.append(record)

    #if 'token' in kwargs:
    #    return jsonify({ 'refresh_token': kwargs['token'], 'users': output })        

    return jsonify({ 'items': output, 'public_id': other_user_public_id })    

    #return jsonify({ 'message': 'In [/items/items/user/'+other_user_public_id+'] with current user ['+public_id+']' }), 501

#------------------------------------------------------------------------------#


#-----------------------------------------------------------------------------#
# system routes
#-----------------------------------------------------------------------------#

@bp.route('/fotos/status', methods=['GET'])
def system_running():

    app.logger.info('Status: system running...')

    return jsonify({ 'message': 'System running...' }), 200


#-----------------------------------------------------------------------------#
# debug and helper functions
#-----------------------------------------------------------------------------#

def _return_document(public_id, item_id):

    app.logger.debug('========================= return_document ===========================')
    collection_name = 'Z' + public_id.replace('-','')
    app.logger.debug('Collection name ['+collection_name+']')
    app.logger.debug('Item id ['+item_id+']')
    record = None
    try:
        app.logger.debug('========================= scream ===========================')
        record = mongo.db[collection_name].find_one({ '_id': ObjectId(item_id) })
        app.logger.debug('========================= wanna? ===========================')
        app.logger.debug(record)
    except Exception as e:
        return False #jsonify({ 'message': 'Something\'s up with the item store. Could not find the item ['+item_id+'] in collection ['+collection_name+']' }), 500

    if record is None:
        return False #jsonify({ 'message': 'Could not find the item ['+item_id+'] in collection ['+collection_name+']' }), 404
    # replace _id with item_id as _id is a returned object 
    record['item_id'] = item_id
    del record['_id']

    return(record)
