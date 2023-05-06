# -*- coding: utf-8 -*-
#

import ipaddress
import json

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from rest_framework.utils.encoders import JSONEncoder

from common.local import add_encrypted_field_set
from common.utils import signer, crypto
from .validators import PortRangeValidator

__all__ = [
    "JsonMixin",
    "JsonDictMixin",
    "JsonListMixin",
    "JsonTypeMixin",
    "JsonCharField",
    "JsonTextField",
    "JsonListCharField",
    "JsonListTextField",
    "JsonDictCharField",
    "JsonDictTextField",
    "EncryptCharField",
    "EncryptTextField",
    "EncryptMixin",
    "EncryptJsonDictTextField",
    "EncryptJsonDictCharField",
    "PortField",
    "PortRangeField",
    "BitChoices",
    "TreeChoices",
    "JSONManyToManyField",
]


class JsonMixin:
    tp = None

    @staticmethod
    def json_decode(data):
        try:
            return json.loads(data)
        except (TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def json_encode(data):
        return json.dumps(data, cls=JSONEncoder)

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value
        return self.json_decode(value)

    def to_python(self, value):
        if value is None:
            return value

        if not isinstance(value, str) or not value.startswith('"'):
            return value
        else:
            return self.json_decode(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.json_encode(value)


class JsonTypeMixin(JsonMixin):
    tp = dict

    def from_db_value(self, value, expression, connection, context=None):
        value = super().from_db_value(value, expression, connection, context)
        if not isinstance(value, self.tp):
            value = self.tp()
        return value

    def to_python(self, value):
        data = super().to_python(value)
        if not isinstance(data, self.tp):
            data = self.tp()
        return data

    def get_prep_value(self, value):
        if not isinstance(value, self.tp):
            value = self.tp()
        return self.json_encode(value)


class JsonDictMixin(JsonTypeMixin):
    tp = dict


class JsonDictCharField(JsonDictMixin, models.CharField):
    description = _("Marshal dict data to char field")


class JsonDictTextField(JsonDictMixin, models.TextField):
    description = _("Marshal dict data to text field")


class JsonListMixin(JsonTypeMixin):
    tp = list


class JsonStrListMixin(JsonListMixin):
    pass


class JsonListCharField(JsonListMixin, models.CharField):
    description = _("Marshal list data to char field")


class JsonListTextField(JsonListMixin, models.TextField):
    description = _("Marshal list data to text field")


class JsonCharField(JsonMixin, models.CharField):
    description = _("Marshal data to char field")


class JsonTextField(JsonMixin, models.TextField):
    description = _("Marshal data to text field")


class EncryptMixin:
    """
    EncryptMixin要放在最前面
    """

    def decrypt_from_signer(self, value):
        return signer.unsign(value) or ""

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return value

        value = force_text(value)
        plain_value = crypto.decrypt(value)

        # 如果没有解开，使用原来的signer解密
        if not plain_value:
            plain_value = self.decrypt_from_signer(value)

        # 可能和Json mix，所以要先解密，再json
        sp = super()
        if hasattr(sp, "from_db_value"):
            plain_value = sp.from_db_value(plain_value, expression, connection, context)
        return plain_value

    def get_prep_value(self, value):
        if value is None:
            return value

        # 先 json 再解密
        sp = super()
        if hasattr(sp, "get_prep_value"):
            value = sp.get_prep_value(value)
        value = force_text(value)
        # 替换新的加密方式
        return crypto.encrypt(value)


class EncryptTextField(EncryptMixin, models.TextField):
    description = _("Encrypt field using Secret Key")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class EncryptCharField(EncryptMixin, models.CharField):
    @staticmethod
    def change_max_length(kwargs):
        kwargs.setdefault("max_length", 1024)
        max_length = kwargs.get("max_length")
        if max_length < 129:
            max_length = 128
        max_length = max_length * 2
        kwargs["max_length"] = max_length

    def __init__(self, *args, **kwargs):
        self.change_max_length(kwargs)
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        max_length = kwargs.pop("max_length")
        if max_length > 255:
            max_length = max_length // 2
        kwargs["max_length"] = max_length
        return name, path, args, kwargs


class EncryptJsonDictTextField(EncryptMixin, JsonDictTextField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class EncryptJsonDictCharField(EncryptMixin, JsonDictCharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_encrypted_field_set(self.verbose_name)


class PortField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "blank": False,
                "null": False,
                "validators": [MinValueValidator(0), MaxValueValidator(65535)],
            }
        )
        super().__init__(*args, **kwargs)


class TreeChoices(models.Choices):
    @classmethod
    def is_tree(cls):
        return True

    @classmethod
    def branches(cls):
        return [i for i in cls]

    @classmethod
    def tree(cls):
        if not cls.is_tree():
            return []
        root = [_("All"), cls.branches()]
        return [cls.render_node(root)]

    @classmethod
    def render_node(cls, node):
        if isinstance(node, models.Choices):
            return {
                "value": node.name,
                "label": node.label,
            }
        else:
            name, children = node
            return {
                "value": name,
                "label": name,
                "children": [cls.render_node(child) for child in children],
            }

    @classmethod
    def all(cls):
        return [i[0] for i in cls.choices]


class BitChoices(models.IntegerChoices, TreeChoices):
    @classmethod
    def is_tree(cls):
        return False

    @classmethod
    def all(cls):
        value = 0
        for c in cls:
            value |= c.value
        return value


class PortRangeField(models.CharField):
    def __init__(self, **kwargs):
        kwargs['max_length'] = 16
        super().__init__(**kwargs)
        self.validators.append(PortRangeValidator())


class RelatedManager:
    def __init__(self, instance, field):
        self.instance = instance
        self.field = field
        self.value = None

    def set(self, value):
        self.value = value
        self.instance.__dict__[self.field.name] = value

    @staticmethod
    def get_ip_in_q(name, val):
        q = Q()
        if isinstance(val, str):
            val = [val]
        for ip in val:
            if not ip:
                continue
            try:
                if ip == '*':
                    return Q()
                elif '/' in ip:
                    network = ipaddress.ip_network(ip)
                    ips = network.hosts()
                    q |= Q(**{"{}__in".format(name): ips})
                elif '-' in ip:
                    start_ip, end_ip = ip.split('-')
                    start_ip = ipaddress.ip_address(start_ip)
                    end_ip = ipaddress.ip_address(end_ip)
                    q |= Q(**{"{}__range".format(name): (start_ip, end_ip)})
                elif len(ip.split('.')) == 4:
                    q |= Q(**{"{}__exact".format(name): ip})
                else:
                    q |= Q(**{"{}__startswith".format(name): ip})
            except ValueError:
                continue
        return q

    def _get_queryset(self):
        model = apps.get_model(self.field.to)
        value = self.value
        if not value or not isinstance(value, dict):
            return model.objects.none()

        if value["type"] == "all":
            return model.objects.all()
        elif value["type"] == "ids" and isinstance(value.get("ids"), list):
            return model.objects.filter(id__in=value["ids"])
        elif value["type"] == "attrs" and isinstance(value.get("attrs"), list):
            filters = Q()
            excludes = Q()
            for attr in value["attrs"]:
                if not isinstance(attr, dict):
                    continue

                name = attr.get('name')
                val = attr.get('value')
                match = attr.get('match', 'exact')
                rel = attr.get('rel', 'and')
                if name is None or val is None:
                    continue

                if val == '*':
                    filters = Q()
                    break

                if match == 'ip_in':
                    q = self.get_ip_in_q(name, val)
                elif match in ("exact", "contains", "startswith", "endswith", "regex"):
                    lookup = "{}__{}".format(name, match)
                    q = Q(**{lookup: val})
                elif match == "not":
                    q = ~Q(**{name: val})
                elif match == "in" and isinstance(val, list):
                    if '*' not in val:
                        lookup = "{}__in".format(name)
                        q = Q(**{lookup: val})
                    else:
                        q = Q()
                else:
                    q = Q(**{name: val})

                if rel == 'or':
                    filters |= q
                elif rel == 'not':
                    excludes |= q
                else:
                    filters &= q
            return model.objects.filter(filters).exclude(excludes)
        else:
            return model.objects.none()

    def all(self):
        return self._get_queryset()

    def filter(self, *args, **kwargs):
        queryset = self._get_queryset()
        return queryset.filter(*args, **kwargs)


class JSONManyToManyDescriptor:
    def __init__(self, field):
        self.field = field
        self._is_setting = False

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        if not hasattr(instance, "_related_manager_cache"):
            instance._related_manager_cache = {}
        if self.field.name not in instance._related_manager_cache:
            manager = RelatedManager(instance, self.field)
            instance._related_manager_cache[self.field.name] = manager
        manager = instance._related_manager_cache[self.field.name]
        return manager

    def __set__(self, instance, value):
        if instance is None:
            return

        if not hasattr(instance, "_related_manager_cache"):
            instance._related_manager_cache = {}

        if self.field.name not in instance._related_manager_cache:
            manager = self.__get__(instance, instance.__class__)
        else:
            manager = instance._related_manager_cache[self.field.name]

        if isinstance(value, RelatedManager):
            value = value.value
        manager.set(value)


class JSONManyToManyField(models.JSONField):
    def __init__(self, to, *args, **kwargs):
        self.to = to
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, JSONManyToManyDescriptor(self))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['to'] = self.to
        return name, path, args, kwargs

    @staticmethod
    def check_value(val):
        if not val:
            return val
        e = ValueError(_(
            "Invalid JSON data for JSONManyToManyField, should be like "
            "{'type': 'all'} or {'type': 'ids', 'ids': []} "
            "or {'type': 'attrs', 'attrs': [{'name': 'ip', 'match': 'exact', 'value': 'value', 'rel': 'and|or|not'}}"
        ))
        if not isinstance(val, dict):
            raise e
        if val["type"] not in ["all", "ids", "attrs"]:
            raise ValueError(_('Invalid type, should be "all", "ids" or "attrs"'))
        if val["type"] == "ids":
            if not isinstance(val["ids"], list):
                raise ValueError(_("Invalid ids for ids, should be a list"))
        elif val["type"] == "attrs":
            if not isinstance(val["attrs"], list):
                raise ValueError(_("Invalid attrs, should be a list of dict"))
            for attr in val["attrs"]:
                if not isinstance(attr, dict):
                    raise ValueError(_("Invalid attrs, should be a list of dict"))
                if 'name' not in attr or 'value' not in attr:
                    raise ValueError(_("Invalid attrs, should be has name and value"))

    def get_db_prep_value(self, value, connection, prepared=False):
        return self.get_prep_value(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, RelatedManager):
            value = value.value
        self.check_value(value)
        return json.dumps(value)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if not isinstance(value, dict):
            raise ValidationError("Invalid JSON data for JSONManyToManyField.")
