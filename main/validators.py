import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_username_latin(value):
    if len(value) < 6:
        raise ValidationError(_('Логин должен содержать минимум 6 символов'))
    if not re.match(r'^[a-zA-Z0-9]+$', value):
        raise ValidationError(_('Логин может содержать только латинские буквы и цифры'))


def validate_password_strength(value):
    if len(value) < 8:
        raise ValidationError(_('Пароль должен содержать минимум 8 символов'))


def validate_fio(value):
    if value and not re.match(r'^[А-Яа-яЁё\s]+$', value):
        raise ValidationError(_('ФИО может содержать только кириллицу и пробелы'))
    if value and len(value.strip()) < 3:
        raise ValidationError(_('ФИО слишком короткое'))


def validate_phone(value):
    pattern = r'^8 \(\d{3}\) \d{3}-\d{2}-\d{2}$'
    if value and not re.match(pattern, value):
        raise ValidationError(_('Формат телефона: 8 (ХХХ) ХХХ-ХХ-ХХ'))