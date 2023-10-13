class HTTPErrorException(Exception):
    """Сервер вернул код ошибки HTTP в ответ на сделанный запрос."""


class TimeoutException(Exception):
    """Время запроса истекло."""
