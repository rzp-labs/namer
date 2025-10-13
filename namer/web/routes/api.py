"""
Defines the api routes of a Flask webserver for namer.
"""

from pathlib import Path
from queue import Queue
from typing import Any, Union

from flask import Blueprint, jsonify, render_template, request
from flask.wrappers import Response
from loguru import logger

from namer.command import make_command_relative_to, move_command_files
from namer.configuration import NamerConfig
from namer.web.actions import delete_file, get_failed_files, get_phash_results, get_queue_size, get_queued_files, get_search_results, human_format, read_failed_log_file


def get_routes(config: NamerConfig, command_queue: Queue) -> Blueprint:
    """
    Builds a blueprint for flask with passed in context, the NamerConfig.
    """
    blueprint = Blueprint('api', __name__, url_prefix='/api')

    @blueprint.route('/v1/render', methods=['POST'])
    def render() -> Response:
        data = request.json

        res: Union[bool, dict[str, Any]] = False
        if data:
            template: str = data.get('template')
            client_data = data.get('data')

            active_page: str = data.get('url')
            if config.web_root and config.web_root != '':
                active_page = active_page.replace(config.web_root, '') if active_page.startswith(config.web_root) else active_page
            active_page = active_page.lstrip('/')

            template_file = f'render/{template}.html'
            response = render_template(template_file, data=client_data, config=config, active_page=active_page)

            res = {
                'response': response,
            }

        return jsonify(res)

    @blueprint.route('/v1/get_files', methods=['POST'])
    def get_files() -> Response:
        data = get_failed_files(config)
        return jsonify(data)

    @blueprint.route('/v1/get_queued', methods=['POST'])
    def get_queued() -> Response:
        data = get_queued_files(command_queue, config)
        return jsonify(data)

    @blueprint.route('/v1/get_search', methods=['POST'])
    def get_search() -> Response:
        data = request.json

        res: Any = False
        if data:
            page = data['page'] if 'page' in data else 1
            res = get_search_results(data['query'], data['type'], data['file'], config, page=page)

        return jsonify(res)

    @blueprint.route('/v1/get_phash', methods=['POST'])
    def get_phash() -> Response:
        data = request.json

        res: Any = False
        if data:
            res = get_phash_results(data['file'], data['type'], config)

        return jsonify(res)

    @blueprint.route('/v1/get_queue', methods=['POST'])
    @logger.catch(reraise=True)
    def get_queue() -> Response:
        queue_size = get_queue_size(command_queue)
        res = human_format(queue_size)

        return jsonify(res)

    @blueprint.route('/v1/rename', methods=['POST'])
    @logger.catch(reraise=True)
    def rename() -> Response:
        data = request.json

        res: Any = False
        if data:
            failed_dir = config.failed_dir
            work_dir = config.work_dir
            if failed_dir is None or work_dir is None:
                raise ValueError('NamerConfig.failed_dir and NamerConfig.work_dir must be configured for rename operations')

            if 'file' not in data or 'scene_id' not in data:
                raise ValueError('Request must contain "file" and "scene_id" fields')

            movie = failed_dir / Path(data['file'])
            command = make_command_relative_to(movie, failed_dir, config=config, is_auto=False)
            moved_command = move_command_files(command, work_dir, is_auto=False)
            if moved_command:
                moved_command.tpdb_id = data['scene_id']
                command_queue.put(moved_command)  # Todo pass selection

        return jsonify(res)

    @blueprint.route('/v1/delete', methods=['POST'])
    def delete() -> Response:
        data = request.json

        res: Any = False
        if data:
            res = delete_file(data['file'], config)

        return jsonify(res)

    @blueprint.route('/v1/read_failed_log', methods=['POST'])
    def read_failed_log() -> Response:
        data = request.json

        res: Any = False
        if data:
            # fmt: off
            res = {
                'file': data['file'],
                'data': read_failed_log_file(data['file'], config)
            }

        return jsonify(res)

    @blueprint.route('/healthcheck', methods=['GET'])
    def healthcheck() -> Response:
        # fmt: off
        res = {
            'status': 'OK',
        }

        return jsonify(res)

    return blueprint
