import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_uploaded_files(file_storage_list, subfolder="requests") -> list:
    """Validate and persist a list of werkzeug FileStorage objects.
    Returns a list of stored relative filenames (subfolder/uuid_originalname).
    Invalid files are silently skipped (validated again at form layer).
    """
    saved = []
    if not file_storage_list:
        return saved

    target_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(target_dir, exist_ok=True)

    for file_storage in file_storage_list:
        if not file_storage or not file_storage.filename:
            continue
        if not allowed_file(file_storage.filename):
            continue
        original = secure_filename(file_storage.filename)
        unique_name = f"{uuid.uuid4().hex[:10]}_{original}"
        full_path = os.path.join(target_dir, unique_name)
        file_storage.save(full_path)
        saved.append(f"{subfolder}/{unique_name}")

    return saved


def save_public_image(file_storage, subfolder="portfolio"):
    """Save a single image under app/static/images/<subfolder>/ so it is publicly
    servable via url_for('static', ...) with no authentication required.
    Returns the relative static path (e.g. 'images/portfolio/xxx.png') or None.
    """
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in {"png", "jpg", "jpeg", "webp"}:
        return None

    target_dir = os.path.join(current_app.static_folder, "images", subfolder)
    os.makedirs(target_dir, exist_ok=True)

    original = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex[:10]}_{original}"
    file_storage.save(os.path.join(target_dir, unique_name))
    return f"images/{subfolder}/{unique_name}"


def delete_file(relative_path: str):
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path)
    if os.path.exists(full_path):
        os.remove(full_path)
