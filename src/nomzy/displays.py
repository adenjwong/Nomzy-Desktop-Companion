from PySide6.QtCore import QPoint, QRect, QSize


def screen_index_for_point(
    geometries: list[QRect],
    point: QPoint,
) -> int | None:
    if not geometries:
        return None

    for index, geometry in enumerate(geometries):
        if geometry.contains(point):
            return index

    return min(
        range(len(geometries)),
        key=lambda index: _distance_squared(point, geometries[index]),
    )


def clamp_window_position(
    position: QPoint,
    window_size: QSize,
    bounds: QRect,
) -> QPoint:
    maximum_x = max(
        bounds.left(),
        bounds.right() - window_size.width() + 1,
    )
    maximum_y = max(
        bounds.top(),
        bounds.bottom() - window_size.height() + 1,
    )
    return QPoint(
        max(bounds.left(), min(position.x(), maximum_x)),
        max(bounds.top(), min(position.y(), maximum_y)),
    )


def normalized_position(point: QPoint, bounds: QRect) -> tuple[float, float]:
    horizontal_span = max(1, bounds.width() - 1)
    vertical_span = max(1, bounds.height() - 1)
    return (
        max(0.0, min((point.x() - bounds.left()) / horizontal_span, 1.0)),
        max(0.0, min((point.y() - bounds.top()) / vertical_span, 1.0)),
    )


def position_from_normalized(
    relative_x: float,
    relative_y: float,
    bounds: QRect,
) -> QPoint:
    return QPoint(
        bounds.left() + round(relative_x * max(1, bounds.width() - 1)),
        bounds.top() + round(relative_y * max(1, bounds.height() - 1)),
    )


def remap_point(point: QPoint, old_bounds: QRect, new_bounds: QRect) -> QPoint:
    relative_x, relative_y = normalized_position(point, old_bounds)
    return position_from_normalized(relative_x, relative_y, new_bounds)


def _distance_squared(point: QPoint, geometry: QRect) -> int:
    if point.x() < geometry.left():
        distance_x = geometry.left() - point.x()
    elif point.x() > geometry.right():
        distance_x = point.x() - geometry.right()
    else:
        distance_x = 0

    if point.y() < geometry.top():
        distance_y = geometry.top() - point.y()
    elif point.y() > geometry.bottom():
        distance_y = point.y() - geometry.bottom()
    else:
        distance_y = 0

    return distance_x * distance_x + distance_y * distance_y
