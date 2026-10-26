"""Monta os dados que o portfólio mostra a partir da API do GitHub."""
import re
from collections import Counter
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache

from .client import GitHubClient, GitHubError

SEARCH_PAGE_SIZE = 100
SEARCH_MAX_PAGES = 10  # a busca do GitHub devolve no máximo 1000 resultados

CONTRIBUTIONS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def make_client():
    return GitHubClient(token=settings.GITHUB_TOKEN)


def _today():
    return datetime.now(ZoneInfo(settings.TIME_ZONE)).date()


# ---------------------------------------------------------------- cache

def cached(key, loader):
    """Devolve `(dados, desatualizado)`. Se o GitHub falhar, usa a última cópia boa."""
    fresh = cache.get(key)
    if fresh is not None:
        return fresh, False
    try:
        data = loader()
    except GitHubError:
        stale = cache.get(f'{key}:stale')
        if stale is not None:
            return stale, True
        raise
    cache.set(key, data, settings.GITHUB_CACHE_SECONDS)
    cache.set(f'{key}:stale', data, settings.GITHUB_STALE_SECONDS)
    return data, False


# ---------------------------------------------------------------- helpers

def contribution_levels(counts):
    """Converte contagens diárias em níveis de 0 a 4, por quartis dos dias ativos."""
    active = sorted(c for c in counts if c > 0)
    if not active:
        return lambda count: 0
    q1, q2, q3 = (active[int(len(active) * p)] for p in (0.25, 0.5, 0.75))

    def level(count):
        if count <= 0:
            return 0
        return 1 + (count > q1) + (count > q2) + (count > q3)

    return level


def build_weeks(counts_by_day, start, end):
    """Agrupa os dias em semanas (domingo = 0), com o nível de cada dia."""
    days = []
    cursor = start
    while cursor <= end:
        days.append((cursor, counts_by_day.get(cursor.isoformat(), 0)))
        cursor += timedelta(days=1)
    level = contribution_levels([count for _, count in days])
    weeks, week = [], []
    for day, count in days:
        weekday = (day.weekday() + 1) % 7
        if weekday == 0 and week:
            weeks.append(week)
            week = []
        week.append({'date': day.isoformat(), 'count': count, 'level': level(count), 'weekday': weekday})
    if week:
        weeks.append(week)
    return weeks


def last_page(headers):
    """Lê o total de páginas do cabeçalho Link (com per_page=1, é o total de itens)."""
    match = re.search(r'[?&]page=(\d+)>;\s*rel="last"', headers.get('Link', '') or '')
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------- resumo

def build_summary():
    client, username = make_client(), settings.GITHUB_USERNAME
    user, _ = client.get(f'/users/{username}')
    repos, _ = client.get(f'/users/{username}/repos', {'per_page': 100, 'type': 'owner', 'sort': 'pushed'})
    orgs, _ = client.get(f'/users/{username}/orgs')

    commits_total = None
    try:
        found, _ = client.get('/search/commits', {'q': f'author:{username}', 'per_page': 1})
        commits_total = found.get('total_count')
    except GitHubError:
        pass  # o resto do resumo continua útil sem esse número

    own = [repo for repo in repos if not repo.get('fork')]
    languages = Counter(repo['language'] for repo in own if repo.get('language'))
    language_total = sum(languages.values())

    return {
        'username': username,
        'name': user.get('name') or username,
        'avatar_url': user.get('avatar_url'),
        'profile_url': user.get('html_url'),
        'bio': user.get('bio'),
        'followers': user.get('followers'),
        'public_repos': user.get('public_repos'),
        'member_since': user.get('created_at'),
        'commits_total': commits_total,
        'organizations': [
            {'login': org['login'], 'avatar_url': org.get('avatar_url')} for org in orgs
        ],
        'languages': [
            {'name': name, 'repos': count, 'percent': round(100 * count / language_total)}
            for name, count in languages.most_common(6)
        ],
    }


# ---------------------------------------------------------------- calendário

def _contributions_graphql(client, username, start, end):
    data = client.graphql(CONTRIBUTIONS_QUERY, {
        'login': username,
        'from': f'{start.isoformat()}T00:00:00Z',
        'to': f'{end.isoformat()}T23:59:59Z',
    })
    collection = data['user']['contributionsCollection']
    calendar = collection['contributionCalendar']
    counts = {
        day['date']: day['contributionCount']
        for week in calendar['weeks'] for day in week['contributionDays']
    }
    return {
        'source': 'graphql',
        'total': calendar['totalContributions'],
        'weeks': build_weeks(counts, start, end),
        'totals': {
            'commits': collection['totalCommitContributions'],
            'pull_requests': collection['totalPullRequestContributions'],
            'reviews': collection['totalPullRequestReviewContributions'],
            'issues': collection['totalIssueContributions'],
            'repositories': collection['totalRepositoriesWithContributedCommits'],
        },
        'start': start.isoformat(),
        'end': end.isoformat(),
        'truncated': False,
    }


def _contributions_search(client, username, start, end):
    """Sem token: conta os commits públicos do período pela busca do GitHub."""
    tz = ZoneInfo(settings.TIME_ZONE)
    counts, fetched, total = Counter(), 0, 0
    oldest = end
    for page in range(1, SEARCH_MAX_PAGES + 1):
        found, _ = client.get('/search/commits', {
            'q': f'author:{username} author-date:>={start.isoformat()}',
            'sort': 'author-date', 'order': 'desc',
            'per_page': SEARCH_PAGE_SIZE, 'page': page,
        })
        total = found.get('total_count', 0)
        items = found.get('items', [])
        for item in items:
            moment = datetime.fromisoformat(item['commit']['author']['date'].replace('Z', '+00:00'))
            day = moment.astimezone(tz).date()
            counts[day.isoformat()] += 1
            oldest = min(oldest, day)
        fetched += len(items)
        if len(items) < SEARCH_PAGE_SIZE or fetched >= total:
            break
    truncated = fetched < total
    window_start = oldest if truncated else start
    repositories = None
    return {
        'source': 'search',
        'total': fetched,
        'weeks': build_weeks(counts, window_start, end),
        'totals': {'commits': fetched, 'pull_requests': None, 'reviews': None,
                   'issues': None, 'repositories': repositories},
        'start': window_start.isoformat(),
        'end': end.isoformat(),
        'truncated': truncated,
    }


def build_contributions():
    client, username = make_client(), settings.GITHUB_USERNAME
    end = _today()
    start = end - timedelta(days=364)
    if client.token:
        return _contributions_graphql(client, username, start, end)
    return _contributions_search(client, username, start, end)


# ---------------------------------------------------------------- atividade

def build_activity(limit=8):
    client, username = make_client(), settings.GITHUB_USERNAME
    found, _ = client.get('/search/commits', {
        'q': f'author:{username}', 'sort': 'author-date', 'order': 'desc', 'per_page': 30,
    })
    commits = []
    for item in found.get('items', []):
        message = (item['commit']['message'] or '').split('\n')[0].strip()
        if not message or message.lower().startswith('merge '):
            continue
        commits.append({
            'repo': item['repository']['full_name'],
            'message': message[:120],
            'sha': item['sha'][:7],
            'url': item['html_url'],
            'date': item['commit']['author']['date'],
        })
        if len(commits) == limit:
            break
    return {'commits': commits}


# ---------------------------------------------------------------- projetos

def _project(client, username, full_name):
    repo, _ = client.get(f'/repos/{full_name}')
    mine = total = None
    try:
        data, headers = client.get(f'/repos/{full_name}/commits', {'author': username, 'per_page': 1})
        mine = last_page(headers) or len(data)
        data, headers = client.get(f'/repos/{full_name}/commits', {'per_page': 1})
        total = last_page(headers) or len(data)
    except GitHubError as error:
        if error.code != 'empty':
            raise
    return {
        'repo': repo['full_name'],
        'description': repo.get('description'),
        'language': repo.get('language'),
        'topics': repo.get('topics', []),
        'stars': repo.get('stargazers_count', 0),
        'url': repo['html_url'],
        'homepage': repo.get('homepage') or None,
        'archived': repo.get('archived', False),
        'pushed_at': repo.get('pushed_at'),
        'my_commits': mine,
        'total_commits': total,
    }


def build_projects():
    client, username = make_client(), settings.GITHUB_USERNAME
    projects, failed = [], []
    for full_name in settings.GITHUB_FEATURED_REPOS:
        try:
            projects.append(_project(client, username, full_name))
        except GitHubError as error:
            if error.code in ('rate_limited', 'unreachable'):
                raise  # sem o GitHub não adianta tentar os próximos
            failed.append(full_name)
    return {'projects': projects, 'unavailable': failed}
