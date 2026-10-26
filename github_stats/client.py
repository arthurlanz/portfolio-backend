"""Cliente mínimo da API do GitHub (REST e GraphQL), sem dependências externas."""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

API_ROOT = 'https://api.github.com'


class GitHubError(Exception):
    """Falha ao consultar o GitHub. `code` diz o motivo para quem chama."""

    def __init__(self, code, message, status=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class GitHubClient:
    def __init__(self, token='', timeout=8):
        self.token = token
        self.timeout = timeout

    def _headers(self):
        headers = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'portfolio-backend',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def _request(self, path, params=None, body=None):
        """Faz a chamada e devolve `(json, headers)`. Levanta `GitHubError`."""
        url = path if path.startswith('http') else f'{API_ROOT}{path}'
        if params:
            url = f'{url}?{urllib.parse.urlencode(params)}'
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, headers=self._headers())
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode() or 'null')
                return payload, response.headers
        except urllib.error.HTTPError as error:
            if error.code in (403, 429) and error.headers.get('X-RateLimit-Remaining') == '0':
                raise GitHubError('rate_limited', 'Limite de requisições do GitHub atingido.', error.code)
            if error.code == 404:
                raise GitHubError('not_found', 'Recurso não encontrado no GitHub.', error.code)
            if error.code == 409:
                raise GitHubError('empty', 'Repositório sem commits.', error.code)
            if error.code == 401:
                raise GitHubError('unauthorized', 'Token do GitHub inválido.', error.code)
            raise GitHubError('github_error', f'O GitHub respondeu {error.code}.', error.code)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            logger.warning('GitHub inacessível: %s', error)
            raise GitHubError('unreachable', 'Não foi possível falar com o GitHub.')

    def get(self, path, params=None):
        return self._request(path, params=params)

    def graphql(self, query, variables):
        data, _ = self._request('/graphql', body={'query': query, 'variables': variables})
        if data.get('errors'):
            raise GitHubError('graphql_error', data['errors'][0].get('message', 'Erro no GraphQL.'))
        return data['data']
