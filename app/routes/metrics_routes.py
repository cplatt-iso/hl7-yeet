# --- START OF FILE app/routes/metrics_routes.py ---

from __future__ import annotations

import csv
import io
from typing import Iterable

from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError

from .. import crud, schemas
from ..auth_utils import auth_required, get_authenticated_user
from ..extensions import db

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


def _csv_response(fieldnames: Iterable[str], rows: list[dict], filename: str) -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(fieldnames))
    writer.writeheader()
    for row in rows:
        writer.writerow({key: ('' if row.get(key) is None else row.get(key)) for key in fieldnames})
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@metrics_bp.route('/runs', methods=['GET'])
@auth_required()
def list_run_metrics():
    user = get_authenticated_user()
    try:
        filters = schemas.RunMetricsListFilters.model_validate(dict(request.args))
    except ValidationError as exc:
        return jsonify({'error': exc.errors()}), 422

    run_dicts = crud.list_run_metrics(
        db,
        user_id=user.id,
        is_admin=user.is_admin,
        template_id=filters.template_id,
        status=filters.status,
        start_at=filters.start_at,
        end_at=filters.end_at,
        limit=filters.limit,
    )

    run_models = [schemas.SimulationRunMetricsResponse.model_validate(item) for item in run_dicts]

    orders_per_second_values = [item.orders_per_second for item in run_models if item.orders_per_second is not None]

    summary = schemas.RunMetricsSummary(
        run_count=len(run_models),
        total_patients=sum(item.total_patients for item in run_models),
        total_worker_jobs=sum(item.worker_job_count for item in run_models),
        total_worker_success=sum(item.worker_job_success_count for item in run_models),
        total_dicom_instances=sum(item.dicom_success_instances for item in run_models),
        total_dicom_bytes=sum(item.dicom_success_bytes for item in run_models),
        average_orders_per_second=(
            sum(orders_per_second_values) / len(orders_per_second_values)
            if orders_per_second_values
            else None
        ),
    )

    if request.args.get('format') == 'csv':
        fieldnames = schemas.SimulationRunMetricsResponse.model_fields.keys()
        rows = [model.model_dump(mode='json') for model in run_models]
        return _csv_response(fieldnames, rows, 'run-metrics.csv')

    response = schemas.RunMetricsListResponse(summary=summary, runs=run_models)
    return jsonify(response.model_dump(mode='json'))


@metrics_bp.route('/workers', methods=['GET'])
@auth_required()
def list_worker_metrics():
    user = get_authenticated_user()
    try:
        filters = schemas.WorkerMetricsListFilters.model_validate(dict(request.args))
    except ValidationError as exc:
        return jsonify({'error': exc.errors()}), 422

    worker_models = [
        schemas.WorkerJobMetricResponse.model_validate(metric)
        for metric in crud.list_worker_metrics(
            db,
            user_id=user.id,
            is_admin=user.is_admin,
            run_id=filters.run_id,
            queue=filters.queue,
            success=filters.success,
            limit=filters.limit,
        )
    ]

    duration_values = [item.duration_ms for item in worker_models if item.duration_ms is not None]

    summary = schemas.WorkerMetricsSummary(
        job_count=len(worker_models),
        success_count=sum(1 for item in worker_models if item.success),
        failure_count=sum(1 for item in worker_models if not item.success),
        average_duration_ms=(
            sum(duration_values) / len(duration_values) if duration_values else None
        ),
    )

    if request.args.get('format') == 'csv':
        fieldnames = schemas.WorkerJobMetricResponse.model_fields.keys()
        rows = [model.model_dump(mode='json') for model in worker_models]
        return _csv_response(fieldnames, rows, 'worker-metrics.csv')

    response = schemas.WorkerMetricsListResponse(summary=summary, metrics=worker_models)
    return jsonify(response.model_dump(mode='json'))


# --- END OF FILE app/routes/metrics_routes.py ---
