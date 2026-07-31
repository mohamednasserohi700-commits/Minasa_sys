from datetime import datetime


def localize_form_labels(form, t, mapping):
    """Overwrite a WTForms form's field labels with translated text at request time.
    `mapping` is {field_name: translation_key}. Fields not in the mapping are left as-is.
    """
    for field_name, key in mapping.items():
        field = getattr(form, field_name, None)
        if field is not None:
            field.label.text = t(key)


def localize_choices(field, t, key_map):
    """Rebuild a SelectField's `choices` list, translating only the visible label
    (the stored `value` — e.g. 'Website', 'Email' — is left untouched so existing
    data and internal logic relying on the English value keep working).
    `key_map` is {value: translation_key}.
    """
    field.choices = [
        (value, t(key_map[value]) if value in key_map else label)
        for value, label in field.choices
    ]


def time_ago(dt: datetime) -> str:
    """Human friendly relative time, e.g. '3 hours ago'."""
    if dt is None:
        return ""
    now = datetime.utcnow()
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)} minute{'s' if int(minutes) != 1 else ''} ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)} hour{'s' if int(hours) != 1 else ''} ago"
    days = hours / 24
    if days < 30:
        return f"{int(days)} day{'s' if int(days) != 1 else ''} ago"
    months = days / 30
    if months < 12:
        return f"{int(months)} month{'s' if int(months) != 1 else ''} ago"
    years = months / 12
    return f"{int(years)} year{'s' if int(years) != 1 else ''} ago"


def file_icon(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mapping = {
        "pdf": "bi-file-earmark-pdf-fill text-danger",
        "doc": "bi-file-earmark-word-fill text-primary",
        "docx": "bi-file-earmark-word-fill text-primary",
        "zip": "bi-file-earmark-zip-fill text-warning",
        "rar": "bi-file-earmark-zip-fill text-warning",
        "png": "bi-file-earmark-image-fill text-success",
        "jpg": "bi-file-earmark-image-fill text-success",
        "jpeg": "bi-file-earmark-image-fill text-success",
        "xlsx": "bi-file-earmark-excel-fill text-success",
        "xls": "bi-file-earmark-excel-fill text-success",
    }
    return mapping.get(ext, "bi-file-earmark-fill text-secondary")
