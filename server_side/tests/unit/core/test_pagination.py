"""Unit tests for the page helpers in `app/core/pagination.py`."""

import allure
import pytest
from pydantic import BaseModel, ValidationError

from app.core.pagination import PaginatedResponse, PaginationParameters

# Allure groups the results by feature. Pagination belongs to no feature.
pytestmark = [allure.feature("server")]


class ExampleItemResponse(BaseModel):
    """An invented item, only for these tests.

    Attributes:
        number: Any number.
    """

    number: int


@pytest.mark.parametrize(
    ("page", "page_size", "expected_offset"),
    [(1, 20, 0), (2, 20, 20), (3, 10, 20), (1, 100, 0)],
)
def test_pagination_parameters_returns_offset_and_limit_when_page_is_given(
    page: int, page_size: int, expected_offset: int
) -> None:
    # Arrange
    pagination = PaginationParameters(page=page, page_size=page_size)

    # Act
    offset = pagination.offset
    limit = pagination.limit

    # Assert
    assert offset == expected_offset
    assert limit == page_size


@pytest.mark.parametrize(
    ("page", "total_items", "expected_beyond"),
    [(1, 47, False), (3, 47, False), (4, 47, True), (1, 0, True), (2, 20, True)],
)
def test_pagination_parameters_finds_page_beyond_last_when_total_items_is_given(
    page: int, total_items: int, expected_beyond: bool
) -> None:
    # Arrange
    pagination = PaginationParameters(page=page, page_size=20)

    # Act
    is_beyond = pagination.is_beyond_last_page(total_items)

    # Assert
    assert is_beyond is expected_beyond


@pytest.mark.parametrize(("page", "page_size"), [(0, 20), (1, 0), (1, 101), (-1, 20)])
def test_pagination_parameters_raises_validation_error_when_values_are_out_of_range(
    page: int, page_size: int
) -> None:
    # Arrange: the values come from the parameters.

    # Act and assert
    with pytest.raises(ValidationError):
        PaginationParameters(page=page, page_size=page_size)


@pytest.mark.parametrize(
    ("total_items", "page_size", "expected_total_pages"),
    [(47, 20, 3), (40, 20, 2), (1, 20, 1), (0, 20, 0), (10**30, 100, 10**28)],
)
def test_paginated_response_calculates_total_pages_when_created(
    total_items: int, page_size: int, expected_total_pages: int
) -> None:
    # Arrange
    pagination = PaginationParameters(page=1, page_size=page_size)

    # Act
    response = PaginatedResponse[ExampleItemResponse].create(
        items=[], total_items=total_items, pagination=pagination
    )

    # Assert: rounded up, exact even for very large numbers, 0 for no items.
    assert response.total_pages == expected_total_pages


def test_paginated_response_has_envelope_fields_when_created() -> None:
    # Arrange
    pagination = PaginationParameters(page=2, page_size=20)
    items = [ExampleItemResponse(number=21), ExampleItemResponse(number=22)]

    # Act
    response = PaginatedResponse[ExampleItemResponse].create(
        items=items, total_items=47, pagination=pagination
    )

    # Assert: the envelope of API_DESIGN §1.6.
    assert response.model_dump() == {
        "items": [{"number": 21}, {"number": 22}],
        "page": 2,
        "page_size": 20,
        "total_items": 47,
        "total_pages": 3,
    }


def test_paginated_response_raises_validation_error_when_item_has_wrong_type() -> None:
    # Arrange: an item that is not an `ExampleItemResponse`.
    pagination = PaginationParameters(page=1, page_size=20)

    # Act and assert: the item type is checked.
    with pytest.raises(ValidationError):
        PaginatedResponse[ExampleItemResponse].model_validate(
            {
                "items": [{"number": "not a number"}],
                "page": pagination.page,
                "page_size": pagination.page_size,
                "total_items": 1,
                "total_pages": 1,
            }
        )
