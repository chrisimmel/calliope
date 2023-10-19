class Pagination:
    """
    A helper class to manage pagination on a page showing potentially many rows.
    """
    total_rows: int
    page_size: int
    page: int
    row_offset: int
    num_pages: int
    max_shown_pages: int

    def __init__(
        self,
        total_rows: int,
        page: int,
        page_size: int = 10,
        max_shown_pages: int = 5
    ) -> None:
        """
        Constructs a Pagination object.

        Args:
            total_rows: the total number of displayable rows.
            page: the current page number.
            page_size: the maximum number of rows on a page.
            max_shown_pages: the maximum number of pages to reference in a pagination
            control.
        """
        self.total_rows = total_rows
        self.page = page
        self.page_size = page_size
        self.num_pages = (total_rows // page_size) + 1
        self.max_shown_pages = max_shown_pages

    @property
    def offset(self) -> int:
        """
        The offset to the first row on the page.
        """
        return (self.page - 1) * self.page_size

    @property
    def prev_page(self) -> int:
        """
        The 1-based page number of the previous page, or zero if currently at
        the first page.
        """
        return self.page - 1

    @property
    def next_page(self) -> int:
        """
        The 1-based page number of the next page, or zero if currently at
        the last page.
        """
        return self.page + 1 if self.page < self.num_pages else 0

    @property
    def pages_in_range(self) -> int:
        """
        A generator of pages in the displayable range for use in a pagination control.
        """
        range_start_page = max(1, self.page - self.max_shown_pages // 2)
        range_end_page = min(self.num_pages + 1, range_start_page + self.max_shown_pages)
        for show_page in range(range_start_page, range_end_page):
            yield show_page
