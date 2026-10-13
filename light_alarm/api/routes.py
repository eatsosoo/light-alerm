"""Translate HTTP input into repository operations and alarm jobs."""

from flask import Blueprint, jsonify, request, url_for


def json_object():
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    return data


def required_text(data, name):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def device_fields(data, user_field):
    raw_port = data.get("port")
    if isinstance(raw_port, bool) or not isinstance(raw_port, (str, int)):
        raise ValueError("port must be an integer between 1 and 65535.")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError("port must be an integer between 1 and 65535.") from error
    if not 1 <= port <= 65535:
        raise ValueError("port must be an integer between 1 and 65535.")
    user = data.get(user_field)
    if isinstance(user, bool) or not isinstance(user, (str, int)) or not str(user).strip():
        raise ValueError(f"{user_field} is required.")
    remark = data.get("remark")
    if remark is not None and not isinstance(remark, str):
        raise ValueError("remark must be a string or null.")
    return (user, required_text(data, "station_name"), required_text(data, "ip"),
            port, required_text(data, "line"), remark)


def create_blueprint(runtime):
    blueprint = Blueprint("api", __name__)
    alarms = runtime.alarms
    repository = runtime.repository

    def accepted(coroutine, mode, scope, duration):
        job_id = runtime.worker.submit_job(coroutine, {
            "source": "api", "mode": mode, "scope": scope, "duration": duration,
        })
        status_url = url_for("api.get_job", job_id=job_id)
        response = jsonify(status="accepted", message="Command queued.", job_id=job_id, status_url=status_url)
        response.headers["Location"] = status_url
        return response, 202

    def command_input():
        data = json_object()
        mode = data.get("mode")
        duration = alarms.validate_command(mode, data.get("duration"))
        return data, mode, duration

    @blueprint.post("/send-command/all")
    def send_all():
        _, mode, duration = command_input()
        return accepted(alarms.send_all(mode, duration), mode, "All", duration)

    @blueprint.post("/send-command/line")
    def send_line():
        data, mode, duration = command_input()
        line = alarms.validate_line(data.get("line"))
        return accepted(alarms.send_line(line, mode, duration), mode, line, duration)

    @blueprint.post("/send-command/device-office")
    def send_office():
        data, mode, duration = command_input()
        line = alarms.validate_line(data.get("line"))
        if mode != "TURN_OFF":
            alarms.validate_command("OFFICE", duration)
        return accepted(alarms.send_device_office(line, mode, duration), mode, f"{line} + OFFICE", duration)

    @blueprint.route("/send-command/turn-off-all/<line>", methods=["GET", "POST"])
    def turn_off(line):
        # GET is retained for existing integrations; new clients should use POST.
        line = alarms.validate_line(line)
        return accepted(alarms.send_device_office(line, "TURN_OFF", 0), "TURN_OFF", f"{line} + OFFICE", 0)

    @blueprint.get("/jobs/<job_id>")
    def get_job(job_id):
        job = runtime.worker.get_job(job_id)
        if job is None:
            return jsonify(status="error", message="Job not found or expired."), 404
        return jsonify(job)

    @blueprint.post("/create_device")
    def create_device():
        repository.create(*device_fields(json_object(), "user_code_created"))
        return jsonify(status="success", message="Device created successfully."), 201

    @blueprint.put("/update_device/<int:keyid>")
    def update_device(keyid):
        if repository.update(keyid, *device_fields(json_object(), "user_code_updated")) == 0:
            return jsonify(status="error", message="Device not found."), 404
        return jsonify(status="success", message="Device updated successfully.")

    @blueprint.delete("/delete_device/<int:keyid>")
    def delete_device(keyid):
        if repository.delete(keyid) == 0:
            return jsonify(status="error", message="Device not found."), 404
        return jsonify(status="success", message="Device deleted successfully.")

    @blueprint.get("/get_device/<int:keyid>")
    def get_device(keyid):
        device = repository.get_by_id(keyid)
        if device is None:
            return jsonify(status="error", message="Device not found."), 404
        return jsonify(status="success", device=device)

    @blueprint.get("/get_devices_by_line/<line>")
    def get_line(line):
        return jsonify(status="success", devices=repository.get_by_line(alarms.validate_line(line)))

    @blueprint.get("/get-all-devices")
    def get_all():
        return jsonify(status="success", devices=repository.get_all())

    @blueprint.get("/get-all-lines")
    def get_lines():
        return jsonify(status="success", lines=repository.get_lines())

    return blueprint
