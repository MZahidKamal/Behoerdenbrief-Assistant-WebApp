"""API tests: `page` and `page_size` in a list route (API_DESIGN §1.6)."""

from collections.abc import AsyncIterator
from typing import Annotated

import allure
import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.pagination import (
    PaginatedResponse,
    PaginationParameters,
    get_pagination_parameters,
)
from app.main import create_app

# Allure groups the results by feature. Pagination belongs to no feature.
pytestmark = [allure.feature("server")]

# An invented list of 47 items, like 47 letters of one user.
EXAMPLE_ITEM_COUNT = 47


class ExampleItemResponse(BaseModel):
    """An invented list item, only for these tests.

    Attributes:
        number: The position of the item, starting at 1.
    """

    number: int


@pytest.fixture
async def pagination_client() -> AsyncIterator[AsyncClient]:
    """Give an HTTP client for the real app with one list route.

    Yields:
        A client that talks to the app in memory.
    """
    application = create_app()

    # The route works like a later repository: count first, then load only
    # an existing page.
    @application.get("/test/example-items")
    async def list_example_items(
        pagination: Annotated[PaginationParameters, Depends(get_pagination_parameters)],
    ) -> PaginatedResponse[ExampleItemResponse]:
        total_items = EXAMPLE_ITEM_COUNT
        if pagination.is_beyond_last_page(total_items):
            page_items: list[ExampleItemResponse] = []
        else:
            first_number = pagination.offset + 1
            last_number = min(pagination.offset + pagination.limit, total_items)
            page_items = [
                ExampleItemResponse(number=number)
                for number in range(first_number, last_number + 1)
            ]
        return PaginatedResponse[ExampleItemResponse].create(
            items=page_items, total_items=total_items, pagination=pagination
        )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        yield client


async def test_list_returns_first_page_of_20_when_no_parameters_are_given(
    pagination_client: AsyncClient,
) -> None:
    # Arrange: no `page` and no `page_size`.

    # Act
    response = await pagination_client.get("/test/example-items")

    # Assert: the defaults of API_DESIGN §1.6.
    body = response.json()
    assert response.status_code == 200
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_items"] == 47
    assert body["total_pages"] == 3
    assert [item["number"] for item in body["items"]] == list(range(1, 21))


async def test_list_returns_last_items_when_last_page_is_asked(
    pagination_client: AsyncClient,
) -> None:
    # Arrange: page 3 of 3 has the items 41 to 47.

    # Act
    response = await pagination_client.get(
        "/test/example-items", params={"page": "3", "page_size": "20"}
    )

    # Assert
    assert [item["number"] for item in response.json()["items"]] == list(range(41, 48))


@pytest.mark.parametrize("page", ["4", str(10**30)])
async def test_list_returns_empty_items_when_page_is_beyond_last(
    pagination_client: AsyncClient, page: str
) -> None:
    # Arrange: a page after the last one, also a huge number.

    # Act
    response = await pagination_client.get("/test/example-items", params={"page": page})

    # Assert: an empty page, not an error (API_DESIGN §1.6).
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total_items"] == 47


@pytest.mark.parametrize(
    ("parameters", "expected_pointer", "expected_code"),
    [
        ({"page": "0"}, "/query/page", "out_of_range"),
        ({"page": "abc"}, "/query/page", "invalid_format"),
        ({"page_size": "0"}, "/query/page_size", "out_of_range"),
        ({"page_size": "101"}, "/query/page_size", "out_of_range"),
    ],
)
async def test_list_returns_422_validation_failed_when_parameter_is_wrong(
    pagination_client: AsyncClient,
    parameters: dict[str, str],
    expected_pointer: str,
    expected_code: str,
) -> None:
    # Arrange: the wrong value comes from the parameters.

    # Act
    response = await pagination_client.get("/test/example-items", params=parameters)

    # Assert: Problem Details with the field (API_DESIGN §3.1).
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
    assert [
        (error["pointer"], error["code"]) for error in response.json()["errors"]
    ] == [(expected_pointer, expected_code)]
