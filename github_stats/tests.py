from datetime import date
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from . import services
from .client import GitHubClient, GitHubError


class Headers(dict):
    """Cabeçalhos de resposta falsos."""


def search_item(day, message='Feat: algo', repo='arthurlanz/app', sha='a' * 40):
    return {
        'sha': sha,
        'html_url': f'https://github.com/{repo}/commit/{sha}',
        'repository': {'full_name': repo},
        'commit': {'message': message, 'author': {'date': f'{day}T15:00:00Z'}},
    }


class FakeGitHub:
    """Responde às rotas usadas pelos serviços, sem tocar na rede."""

    def __init__(self, routes):
        self.routes = routes
        self.token = ''
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        handler = self.routes[path]
        if isinstance(handler, Exception):
            raise handler
        return handler(params) if callable(handler) else handler


class LevelTests(SimpleTestCase):
    def test_levels_follow_active_day_quartiles(self):
        level = services.contribution_levels([0, 1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(level(0), 0)
        self.assertEqual(level(1), 1)
        self.assertEqual(level(8), 4)

    def test_no_activity_is_always_level_zero(self):
        self.assertEqual(services.contribution_levels([0, 0])(5), 0)

    def test_weeks_start_on_sunday_and_cover_every_day(self):
        weeks = services.build_weeks({'2026-10-25': 3}, date(2026, 10, 22), date(2026, 10, 28))
        days = [day for week in weeks for day in week]
        self.assertEqual(len(days), 7)
        self.assertEqual(weeks[1][0]['date'], '2026-10-25')  # domingo
        self.assertEqual(weeks[1][0]['weekday'], 0)
        self.assertEqual(weeks[1][0]['count'], 3)

    def test_last_page_reads_link_header(self):
        header = {'Link': '<https://api.github.com/r/commits?per_page=1&page=2>; rel="next", '
                          '<https://api.github.com/r/commits?per_page=1&page=86>; rel="last"'}
        self.assertEqual(services.last_page(header), 86)
        self.assertIsNone(services.last_page({}))


class SummaryTests(SimpleTestCase):
    def test_summary_counts_languages_without_forks(self):
        repos = [
            {'language': 'Vue', 'fork': False}, {'language': 'Vue', 'fork': False},
            {'language': 'Python', 'fork': False}, {'language': 'JavaScript', 'fork': True},
            {'language': None, 'fork': False},
        ]
        fake = FakeGitHub({
            '/users/arthurlanz': ({'name': 'Arthur', 'avatar_url': 'a', 'html_url': 'h',
                                   'followers': 4, 'public_repos': 9, 'created_at': '2024-02-27T00:00:00Z'}, {}),
            '/users/arthurlanz/repos': (repos, {}),
            '/users/arthurlanz/orgs': ([{'login': 'DreamTeam-2k26', 'avatar_url': 'x'}], {}),
            '/search/commits': ({'total_count': 731}, {}),
        })
        with patch.object(services, 'make_client', return_value=fake):
            data = services.build_summary()
        self.assertEqual(data['commits_total'], 731)
        self.assertEqual(data['organizations'][0]['login'], 'DreamTeam-2k26')
        self.assertEqual([lang['name'] for lang in data['languages']], ['Vue', 'Python'])
        self.assertEqual(data['languages'][0]['percent'], 67)

    def test_summary_survives_search_failure(self):
        fake = FakeGitHub({
            '/users/arthurlanz': ({'name': None}, {}),
            '/users/arthurlanz/repos': ([], {}),
            '/users/arthurlanz/orgs': ([], {}),
            '/search/commits': GitHubError('rate_limited', 'limite'),
        })
        with patch.object(services, 'make_client', return_value=fake):
            data = services.build_summary()
        self.assertIsNone(data['commits_total'])
        self.assertEqual(data['name'], 'arthurlanz')


class ContributionTests(SimpleTestCase):
    def test_search_fallback_buckets_commits_by_day(self):
        items = [search_item('2026-10-20'), search_item('2026-10-20'), search_item('2026-10-24')]
        fake = FakeGitHub({'/search/commits': ({'total_count': 3, 'items': items}, {})})
        with patch.object(services, 'make_client', return_value=fake), \
                patch.object(services, '_today', return_value=date(2026, 10, 26)):
            data = services.build_contributions()
        counts = {day['date']: day['count'] for week in data['weeks'] for day in week}
        self.assertEqual(data['source'], 'search')
        self.assertEqual(data['total'], 3)
        self.assertEqual(counts['2026-10-20'], 2)
        self.assertEqual(counts['2026-10-24'], 1)
        self.assertFalse(data['truncated'])

    def test_search_fallback_flags_truncated_window(self):
        items = [search_item('2026-10-01')] * 100
        fake = FakeGitHub({'/search/commits': ({'total_count': 1500, 'items': items}, {})})
        with patch.object(services, 'make_client', return_value=fake), \
                patch.object(services, '_today', return_value=date(2026, 10, 26)):
            data = services.build_contributions()
        self.assertTrue(data['truncated'])
        self.assertEqual(data['start'], '2026-10-01')

    def test_graphql_is_used_when_there_is_a_token(self):
        class Fake(FakeGitHub):
            def graphql(self, query, variables):
                return {'user': {'contributionsCollection': {
                    'totalCommitContributions': 40, 'totalPullRequestContributions': 6,
                    'totalPullRequestReviewContributions': 2, 'totalIssueContributions': 3,
                    'totalRepositoriesWithContributedCommits': 8,
                    'contributionCalendar': {'totalContributions': 51, 'weeks': [
                        {'contributionDays': [{'date': '2026-10-25', 'contributionCount': 5, 'weekday': 0}]},
                    ]},
                }}}

        fake = Fake({})
        fake.token = 'ghp_x'
        with patch.object(services, 'make_client', return_value=fake), \
                patch.object(services, '_today', return_value=date(2026, 10, 26)):
            data = services.build_contributions()
        self.assertEqual(data['source'], 'graphql')
        self.assertEqual(data['total'], 51)
        self.assertEqual(data['totals']['repositories'], 8)


class ActivityAndProjectTests(SimpleTestCase):
    def test_activity_skips_merge_commits_and_keeps_first_line(self):
        items = [
            search_item('2026-10-24', 'Merge pull request #69 from x/y'),
            search_item('2026-10-24', 'Feat#68-Carregar a foto\n\ncorpo longo', sha='b' * 40),
        ]
        fake = FakeGitHub({'/search/commits': ({'items': items}, {})})
        with patch.object(services, 'make_client', return_value=fake):
            data = services.build_activity()
        self.assertEqual(len(data['commits']), 1)
        self.assertEqual(data['commits'][0]['message'], 'Feat#68-Carregar a foto')
        self.assertEqual(data['commits'][0]['sha'], 'bbbbbbb')

    @override_settings(GITHUB_FEATURED_REPOS=['org/app', 'org/vazio', 'org/sumiu'])
    def test_projects_count_my_commits_and_tolerate_missing_repos(self):
        link = {'Link': '<https://api.github.com/x?per_page=1&page=%d>; rel="last"'}

        def commits(params):
            return ([{}], {'Link': link['Link'] % (24 if 'author' in params else 56)})

        def repo(name):
            return ({'full_name': name, 'html_url': f'https://github.com/{name}', 'stargazers_count': 1}, {})

        fake = FakeGitHub({
            '/repos/org/app': repo('org/app'),
            '/repos/org/app/commits': commits,
            '/repos/org/vazio': repo('org/vazio'),
            '/repos/org/vazio/commits': GitHubError('empty', 'vazio', 409),
            '/repos/org/sumiu': GitHubError('not_found', 'não achei', 404),
        })
        with patch.object(services, 'make_client', return_value=fake):
            data = services.build_projects()
        by_name = {project['repo']: project for project in data['projects']}
        self.assertEqual(by_name['org/app']['my_commits'], 24)
        self.assertEqual(by_name['org/app']['total_commits'], 56)
        self.assertIsNone(by_name['org/vazio']['my_commits'])
        self.assertEqual(data['unavailable'], ['org/sumiu'])


class CacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_serves_stale_copy_when_github_fails(self):
        services.cached('k', lambda: {'ok': 1})
        cache.delete('k')  # expirou a cópia fresca, a antiga continua guardada

        def broken():
            raise GitHubError('unreachable', 'fora do ar')

        data, stale = services.cached('k', broken)
        self.assertEqual(data, {'ok': 1})
        self.assertTrue(stale)

    def test_raises_when_there_is_nothing_cached(self):
        def broken():
            raise GitHubError('unreachable', 'fora do ar')

        with self.assertRaises(GitHubError):
            services.cached('vazio', broken)


class EndpointTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def test_summary_endpoint_returns_data_and_cache_header(self):
        with patch.object(services, 'build_summary', return_value={'username': 'arthurlanz'}):
            response = self.api.get('/api/github/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'username': 'arthurlanz', 'stale': False})
        self.assertIn('max-age=300', response['Cache-Control'])

    def test_endpoint_returns_503_with_a_code_when_github_is_down(self):
        error = GitHubError('unreachable', 'Não foi possível falar com o GitHub.')
        with patch.object(services, 'build_activity', side_effect=error):
            response = self.api.get('/api/github/activity/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'unreachable')

    def test_default_contact_limit_does_not_apply_to_github_endpoints(self):
        with patch.object(services, 'build_projects', return_value={'projects': []}):
            codes = {self.api.get('/api/github/projects/').status_code for _ in range(15)}
        self.assertEqual(codes, {200})

    def test_only_get_is_allowed(self):
        self.assertEqual(self.api.post('/api/github/summary/').status_code, 405)


class ClientTests(SimpleTestCase):
    def test_sends_token_only_when_configured(self):
        self.assertNotIn('Authorization', GitHubClient()._headers())
        self.assertEqual(GitHubClient(token='abc')._headers()['Authorization'], 'Bearer abc')
