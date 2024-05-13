from typing import Union

from django.db.models import Field, Model
from django.db.models.fields.related_descriptors import ForwardOneToOneDescriptor, ForwardManyToOneDescriptor


def frame_column(field: Union[Model, Field]) -> str:
    if isinstance(field, ForwardOneToOneDescriptor) or isinstance(field, ForwardManyToOneDescriptor):
        return field.__dict__['field'].name + '_id'
    return field.__dict__['field'].name

def foreign_frame_column(link: Union[Model, Field], field: Union[Model, Field]) -> str:
    if not (isinstance(link, ForwardOneToOneDescriptor) or isinstance(link, ForwardManyToOneDescriptor)):
        raise RuntimeError(f"Attempt to access a foreign frame column with a link that is not foreign: {link}")
    return link.__dict__['field'].name + "__" + frame_column(field)
