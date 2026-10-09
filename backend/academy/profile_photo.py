import warnings
from io import BytesIO
from uuid import uuid4

from django.http import HttpResponse
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import ProfileSerializer

MAX_BYTES = 5 * 1024 * 1024


class ProfilePhotoView(APIView):
    parser_classes = [MultiPartParser]

    def get(self, request):
        data = User.objects.values_list("photo_data", flat=True).get(pk=request.user.pk)
        if not data:
            return Response({"detail": "No profile photo is available."}, status=404)
        response = HttpResponse(bytes(data), content_type="image/jpeg")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def post(self, request):
        upload = request.FILES.get("photo")
        if set(request.data) != {"photo"} or not upload or upload.size > MAX_BYTES:
            raise ValidationError({"detail": "Choose a JPEG, PNG or WebP image up to 5 MB."})
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(upload) as image:
                    if image.format not in {"JPEG", "PNG", "WEBP"}:
                        raise ValidationError({"detail": "Choose a JPEG, PNG or WebP image up to 5 MB."})
                    if image.width * image.height > 16_000_000:
                        raise ValidationError({"detail": "Image dimensions must not exceed 16 megapixels."})
                    image.load()
                    oriented = ImageOps.exif_transpose(image).convert("RGBA")
                    oriented.thumbnail((512, 512))
                    background = Image.new("RGB", oriented.size, "white")
                    background.paste(oriented, mask=oriented.getchannel("A"))
                    output = BytesIO()
                    background.save(output, format="JPEG", quality=85)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ValidationError({"detail": "This image is invalid or too large to process."}) from error
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            user.photo_data = output.getvalue()
            user.photo_version = uuid4().hex
            user.save(update_fields=["photo_data", "photo_version"])
        return Response(ProfileSerializer(user).data)

    def delete(self, request):
        User.objects.filter(pk=request.user.pk).update(photo_data=None, photo_version="")
        request.user.refresh_from_db()
        return Response(ProfileSerializer(request.user).data)
