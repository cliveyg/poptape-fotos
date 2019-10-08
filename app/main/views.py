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
# return fotos by logged in user - optional pagination with from and to fields
#-----------------------------------------------------------------------------#

@bp.route('/fotos', methods=['GET'])
@require_access_level(10, request)
def get_fotos_by_user(public_id, request):

    offset, sort = 0, 'id_asc'
    limit = int(app.config['PAGE_LIMIT'])

    if 'offset' in request.args:
        offset = int(request.args['offset'])
    if 'limit' in request.args:
        limit = int(request.args['limit'])
    if 'sort' in request.args:
        sort = request.args['sort']

    #TODO: need to get all the items by a user and then pull photos as they're 
    # stored by item_id collections

    starting_id = None
    try:
        starting_id = mongo.db[public_id].find().sort('_id', ASCENDING)
        #results_count = starting_id.count()
    except:
        jsonify({ 'message': 'There\'s a problem with your arguments or mongo or both or something else ;)'}), 400

    if starting_id is None or starting_id.count() == 0:
        return jsonify({ 'message': 'Nowt here chap'}), 404

    app.logger.info("Starting id count is [%s]",str(starting_id.count()))
    if starting_id.count() != 0 and starting_id.count() <= offset:
        return jsonify({ 'message': 'offset is too big'}), 400

    if offset < 0:
        return jsonify({ 'message': 'offset is negative'}), 400

    last_id = starting_id[offset]['_id']
    results_count = starting_id.count()

    fotos = []
    try:
        fotos = mongo.db[public_id].find({'_id': { '$gte': last_id}}).sort('_id', ASCENDING).limit(limit)
    except:
        jsonify({ 'message': 'There\'s a problem with your arguments or the planets are misaligned. Try sacrificing a goat or something...'}), 400

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
        #starting_id = mongo.db[item_id].find().sort('_id', ASCENDING)
        starting_id = mongo.db[item_id].find().sort('metadata.idx', ASCENDING)    
    except:
        jsonify({ 'message': 'There\'s a problem with your arguments or mongo or both or something else ;)'}), 400

    if starting_id.count() == 0 or starting_id is None:
        return jsonify({ 'message': 'Nowt here chap'}), 404

    if starting_id.count() <= offset:
        return jsonify({ 'message': 'offset is too big'}), 400

    if offset < 0:
        return jsonify({ 'message': 'offset is negative'}), 400

    last_id = starting_id[offset]['metadata']['idx']
    results_count = starting_id.count()

    fotos = []
    try:
        #fotos = mongo.db[item_id].find({'_id': { '$gte': last_id}}).sort('_id', ASCENDING).limit(limit)
        fotos = mongo.db[item_id].find({'metadata.idx': { '$gte': last_id}}).sort('metadata.idx', ASCENDING).limit(limit)
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
        next_url = '/fotos/item/'+item_id+'?limit='+str(limit)+'&offset='+str(url_offset_next)+'&sort='+sort
        return_data['next_url'] = next_url

    if offset > 0:
        prev_url = '/fotos/item/'+item_id+'?limit='+str(limit)+'&offset='+str(url_offset_prev)+'&sort='+sort
        return_data['prev_url'] = prev_url

    return jsonify(return_data), 200


#-----------------------------------------------------------------------------#
# create foto by logged in user
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

    # each item has it's own collection that foto data is stored in
    #foto_id = str(uuid.uuid4())
    foto_id = input_data['foto_id']
    item_id = input_data['item_id']
    del input_data['item_id']
    del input_data['foto_id']
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
