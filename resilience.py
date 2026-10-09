"""Bounded retries for transport failures; deterministic errors fail once."""
import errno, http.client, socket, ssl, time, urllib.error

def transient(error):
    if isinstance(error, urllib.error.HTTPError):
        return error.code in (408, 429, 500, 502, 503, 504)
    if isinstance(error, urllib.error.URLError):
        return transient(error.reason)
    if isinstance(error, socket.gaierror):return error.errno==socket.EAI_AGAIN
    if isinstance(error, (http.client.IncompleteRead, ssl.SSLEOFError)):return True
    return isinstance(error, (TimeoutError, ConnectionError, socket.timeout)) or (
        isinstance(error, OSError) and error.errno in (errno.ECONNRESET, errno.ETIMEDOUT, errno.ECONNABORTED))

def retry(operation, attempts=3, sleep=time.sleep):
    for attempt in range(attempts):
        try: return operation()
        except Exception as error:
            if attempt + 1 == attempts or not transient(error): raise
            delay = min(60, 5 * 2**attempt)
            if isinstance(error, urllib.error.HTTPError):
                value = error.headers.get('Retry-After', '') if error.headers else ''
                if value.isdigit(): delay = min(60, max(delay, int(value)))
            print(f'Transient transport failure; retry {attempt+2}/{attempts} in {delay}s', flush=True)
            sleep(delay)

def fetch(req, timeout=120):
    import urllib.request
    def once():
        with urllib.request.urlopen(req, timeout=timeout) as reply: return reply.read()
    return retry(once)
