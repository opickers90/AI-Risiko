import magic
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class MimetypeValidator:
    def __init__(self, mimetypes):
        self.mimetypes = mimetypes

    def __call__(self, value):
        try:
            mime = magic.from_buffer(value.read(2048), mime=True)
            if mime not in self.mimetypes:
                raise ValidationError(_("File type is not allowed."))
        except AttributeError:
            raise ValidationError(_("Unable to detect file type."))


@deconstructible
class FileSizeValidator:
    def __init__(self, max_size_mb):
        self.max_size_mb = max_size_mb

    def __call__(self, value):
        if value.size > self.max_size_mb * 1024 * 1024:
            raise ValidationError(
                "{}: {} MB".format(_("Maximum file upload size"), self.max_size_mb)
            )
