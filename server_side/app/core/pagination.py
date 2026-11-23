"""Page numbers for long lists: query parameters and the response envelope.

A list endpoint that can grow returns one page at a time
(`?page=2&page_size=20`), as in API_DESIGN §1.6. The database skips the items
of the earlier pages (`OFFSET`) and takes one page (`LIMIT`).

Use it in a route like this:

    @router.get("/letters")
    async def list_letters(
        pagination: Annotated[PaginationParameters, Depends(get_pagination_parameters)],
    ) -> PaginatedResponse[LetterListItemResponse]:
        ...
"""

from collections.abc import Sequence
from typing import Annotated, Self

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

# The limits of API_DESIGN §1.6. They are part of the API contract, so they
# are constants and not settings.
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAXIMUM = 100


class PaginationParameters(BaseModel):
    """Which page of a list the client wants.

    Attributes:
        page: The page number, starting at 1.
        page_size: How many items one page has, 1 to 100.
    """

    model_config = ConfigDict(frozen=True)

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=PAGE_SIZE_MAXIMUM)

    @property
    def offset(self) -> int:
        """How many items the database skips (`OFFSET`).

        Returns:
            For example 20 for page 2 with 20 items per page.
        """
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """How many items the database takes at most (`LIMIT`).

        Returns:
            The page size.
        """
        return self.page_size

    def is_beyond_last_page(self, total_items: int) -> bool:
        """Tell whether this page starts after the last item.

        Count the items first. If this returns True, return an empty page
        without the item query. So a huge page number never reaches the
        database as a giant `OFFSET` that it cannot handle.

        Args:
            total_items: How many items the whole list has.

        Returns:
            True if the page has no items (API_DESIGN §1.6: an empty page,
            not an error).
        """
        return self.offset >= total_items


def get_pagination_parameters(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAXIMUM)] = PAGE_SIZE_DEFAULT,
) -> PaginationParameters:
    """Read `page` and `page_size` from the query (a FastAPI dependency).

    A wrong value (for example `page=0` or `page_size=101`) gives
    `422 validation_failed` with the pointer `/query/page` or
    `/query/page_size`.

    Args:
        page: The page number. Default 1.
        page_size: Items per page. Default 20, at most 100.

    Returns:
        The checked parameters.
    """
    return PaginationParameters(page=page, page_size=page_size)


class PaginatedResponse[ItemType](BaseModel):
    """One page of a list, with the numbers of the whole list (API_DESIGN §1.6).

    `ItemType` is the schema of one item, for example
    `PaginatedResponse[LetterListItemResponse]`.

    Attributes:
        items: The items of this page. Empty beyond the last page.
        page: The page number.
        page_size: Items per page.
        total_items: How many items the whole list has.
        total_pages: How many pages the whole list has. 0 for an empty list.
    """

    items: list[ItemType]
    page: int
    page_size: int
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)

    @classmethod
    def create(
        cls,
        items: Sequence[ItemType],
        total_items: int,
        pagination: PaginationParameters,
    ) -> Self:
        """Build the page and calculate the number of pages.

        Args:
            items: The items of this page.
            total_items: How many items the whole list has.
            pagination: The page the client asked for.

        Returns:
            The response, for example 3 pages for 47 items with 20 per page.
        """
        # Round up: 47 items with 20 per page need 3 pages. Whole numbers
        # only, so even very large counts stay exact. 0 items give 0 pages.
        total_pages = (total_items + pagination.page_size - 1) // pagination.page_size
        return cls(
            items=list(items),
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
