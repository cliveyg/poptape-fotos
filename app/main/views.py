# app/main/views.py
# from bson import ObjectId
from app import mongo
from flask import jsonify, request
from flask import current_app as app
from app.main import bp
from app.assertions import assert_valid_schema
from app.decorators import require_access_level
from jsonschema.exceptions import ValidationError as JsonValidationError
import uuid
from urllib.parse import urlencode
# import re

# from pymongo import ASCENDING
# from pymongo import errors as PymongoException

# --------------------------------------------------------------------------- #
# fotos routes
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# return fotos by foto_id. there is a possibility of multiple docs per foto_id
# --------------------------------------------------------------------------- #

@bp.route('/fotos/<foto_id>', methods=['GET'])
# @require_access_level(10, request)
# def get_foto_by_id(public_id, request, foto_id):
def get_foto_by_id(foto_id):

    app.logger.debug("In get_foto_by_id")

    if not is_valid_uuid(foto_id):
        return jsonify({ 'message': 'Invalid UUID'}), 400
    safe_uuid = str(foto_id)

    # can have several docs returned per foto as foto reuse is possible
    records = _return_documents(request, safe_uuid, "foto_id")
    if not records:
        # return jsonify({ 'message': 'Something went pop'}), 500
        # return empty array
        return jsonify({ 'docs': []}), 404

    return jsonify(records), 200

# --------------------------------------------------------------------------- #
# return fotos by current user
# --------------------------------------------------------------------------- #

@bp.route('/fotos', methods=['GET'])
@require_access_level(10, request)
# def get_foto_by_id(public_id, request, foto_id):
def get_fotos_by_current_user(public_id, request):

    app.logger.debug("In get_fotos_by_current_user")

    if not is_valid_uuid(public_id):
        return jsonify({ 'message': 'Invalid UUID'}), 400
    safe_uuid = str(public_id)

    # can have several docs returned per item
    records = _return_documents(request, safe_uuid, "public_id")
    if not records:
        # return jsonify({ 'message': 'Something went pop'}), 500
        # return empty array
        return jsonify({ 'docs': []}), 404

    return jsonify(records), 200

# --------------------------------------------------------------------------- #
# return fotos by item_id.
# --------------------------------------------------------------------------- #

@bp.route('/fotos/item/<item_id>', methods=['GET'])
# @require_access_level(10, request)
# def get_foto_by_id(public_id, request, foto_id):
def get_fotos_by_item(item_id):

    app.logger.debug("In get_fotos_by_item")

    if not is_valid_uuid(item_id):
        return jsonify({ 'message': 'Invalid UUID'}), 400
    safe_uuid = str(item_id)

    # can have several docs returned per item
    records = _return_documents(request, safe_uuid, "item_id")
    if not records:
        # return jsonify({ 'message': 'Something went pop'}), 500
        # return empty array
        return jsonify({ 'docs': []}), 404

    return jsonify(records), 200


#-----------------------------------------------------------------------------#
# create foto by logged in user
#-----------------------------------------------------------------------------#

@bp.route('/fotos', methods=['POST'])
@require_access_level(10, request)
def create_foto(public_id, request):

    input_data = request.get_json()

    app.logger.debug("Creating foto record")

    # validate input against json schemas
    try:
        assert_valid_schema(input_data)
    except JsonValidationError as err:
        return jsonify({ 'message': 'Check ya inputs mate.', 'error': err.message }), 400

    foto_id = input_data['foto_id']
    item_id = input_data['item_id']
    del input_data['item_id']
    del input_data['foto_id']

    current_id = 0
    try:
        for last_id in mongo.db.fotos.find({}, {"_id": 1}).sort({"_id": -1}).limit(1):
            current_id = last_id["_id"]
    except:
        message = { 'message': 'Ooopsy, had trouble fetching last _id' }
        return jsonify(message), 500

    app.logger.debug("current_id is [%d]", current_id)

    try:
        mongo.db.fotos.insert_one({"_id": current_id + 1, "foto_id": foto_id, "item_id": item_id, "public_id": public_id, "metadata": input_data})
    except Exception as e:
        message = { 'message': 'Ooopsy, couldn\'t create mongo document.' }
        app.logger.error("Pymongo error [%s]", str(e))
        if app.config['ENVIRONMENT'] != 'PROD':
             message['error'] = str(e)
        return jsonify(message), 500

    return jsonify({ 'foto_id': foto_id }), 201


# --------------------------------------------------------------------------- #
# system routes
# --------------------------------------------------------------------------- #

@bp.route('/fotos/status', methods=['GET'])
def system_running():

    app.logger.info('Status: system running...')

    return jsonify({ 'message': 'System running...' }), 200


# --------------------------------------------------------------------------- #
# debug and helper functions
# --------------------------------------------------------------------------- #

def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False

def _return_documents(request, in_uuid, in_key):

    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', app.config.get('PAGE_LIMIT', 10)))
        sort = request.args.get('sort', 'id_asc')
        paginate = bool(request.args.get('paginate', False))
    except Exception:
        return False

    match in_key:
        case "foto_id":
            key_object = {"foto_id": in_uuid}
        case "public_id":
            key_object = {"public_id": in_uuid}
        case "item_id":
            key_object = {"item_id": in_uuid}
        case _:
            key_object = {"foto_id": in_uuid}

    try:
        # Get total number of documents
        total_records = mongo.db.fotos.count_documents(key_object) if paginate else None

        query = mongo.db.fotos.find(key_object)
        if sort == 'id_asc':
            query = query.sort([("_id", 1)])
        elif sort == 'id_desc':
            query = query.sort([("_id", -1)])

        if paginate:
            query = query.skip(offset).limit(limit)
        records = list(query)
    except Exception as e:
        return False

    if len(records) == 0:
        return False

    out_docs = []
    for rec in records:
        if '_id' in rec:
            del rec['_id']
        out_docs.append(rec)

    pagination = None
    if paginate:
        path = request.path
        args = request.args.to_dict()
        next_url = prev_url = None

        # next_url logic
        if total_records is not None and (offset + limit) < total_records:
            next_args = args.copy()
            next_args['offset'] = offset + limit
            next_args['limit'] = limit
            next_url = f"{path}?{urlencode(next_args)}"

        # prev_url logic
        if offset > 0:
            prev_args = args.copy()
            prev_args['offset'] = max(0, offset - limit)
            prev_args['limit'] = limit
            prev_url = f"{path}?{urlencode(prev_args)}"

        pagination = {
            "offset": offset,
            "limit": limit,
            "returned": len(out_docs),
            "total": total_records,
        }
        if next_url:
            pagination["next_url"] = next_url
        if prev_url:
            pagination["prev_url"] = prev_url

        return { 'docs': out_docs, 'pagination': pagination }
    else:
        return { 'docs': out_docs }
