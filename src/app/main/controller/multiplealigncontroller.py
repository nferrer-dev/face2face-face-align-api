"""
Copyright 2019 Jorge Torregrosa

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import cv2
import base64
import time
import imghdr
from flask import abort
from flask_restplus import Resource
from werkzeug.datastructures import FileStorage

from ..util.dto import MultipleDetectionImageDto
from ..exception.invalidusageexception import InvalidUsageException
from ..services.facealignservice import FaceAlignService

api = MultipleDetectionImageDto.api
multiple_response = MultipleDetectionImageDto.multiple_response

upload_parser = api.parser()
upload_parser.add_argument('file', required=True, location='files', type=FileStorage, help='Source image')
allowed_image_types = ['gif', 'jpeg', 'bmp', 'png']


@api.errorhandler
def default_error_handler(error):
    return {'message': str(error)}, getattr(error, 'code', 500)


@api.errorhandler(InvalidUsageException)
def handle_invalid_usage_exception(error):
    """
    Handles global exception fired from this namespace.
    :param error: exception fired.
    :return: payload, status code tuple.
    """
    return {'message': error.message}, 400


def is_allowed_file(file):
    """
    Checks if the uploaded file is allowed.
    :param file: uploaded file to check.
    :return: true if is a valid one, false otherwise.
    """
    return file and imghdr.what(file) in allowed_image_types


@api.route('/<size>')
@api.param('size', 'Output size')
class SingleFaceAlign(Resource):
    """
    Single Face Align Resource.
    """
    face_align_service = FaceAlignService()

    @api.doc('Multiple Face Align')
    @api.expect(upload_parser)
    @api.marshal_with(multiple_response)
    def post(self, size):
        """
        Look for all faces in the image and resize them to common dimensions keeping the features in the same position.
        :return: A payload with the data encoded in Base64.
        """
        # Parse request parameters.
        args = upload_parser.parse_args()
        file = args['file']
        size_value = 0

        try:
            size_value = int(size)
        except ValueError:
            abort(400, 'Invalid size value')

        if size_value <= 8 or size_value > 1024:
            abort(400, 'Only sizes between 8 and 1024 are allowed')

        # Perform image content validation.
        if not is_allowed_file(file):
            abort(400, 'Only png, bmp, jpeg or gif files are allowed')

        # Start measuring time.
        t = time.clock()

        # Process uploaded image.
        img_type = imghdr.what(file)
        detected_faces = self.face_align_service.extract_all_faces(file, size_value)

        # Convert each detected face to Base64
        base64_encoded_images = []

        for face in detected_faces:
            data = cv2.imencode('.png', face)[1].tobytes()
            img = base64.b64encode(data).decode('utf-8')
            base64_encoded_images.append(img)

        # Stop measuring time.
        elapsed_time = time.clock() - t

        # Compose response.
        return {
            "processTime": elapsed_time,
            "inputType": img_type,
            "targetSize": size,
            "imageCount": len(base64_encoded_images),
            "data": base64_encoded_images
        }
