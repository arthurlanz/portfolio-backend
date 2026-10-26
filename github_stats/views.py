from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from . import services
from .client import GitHubError


class GithubThrottle(AnonRateThrottle):
    """Os dados vêm do cache, então o limite pode ser bem maior que o do formulário."""
    scope = 'github'
    rate = '120/min'


def respond(key, loader):
    try:
        data, stale = services.cached(key, loader)
    except GitHubError as error:
        return Response({'detail': error.message, 'code': error.code}, status=503)
    response = Response({**data, 'stale': stale})
    response['Cache-Control'] = 'public, max-age=300'
    return response


@api_view(['GET'])
@throttle_classes([GithubThrottle])
def summary(request):
    """Perfil, total de commits, organizações e linguagens."""
    return respond('github:summary', services.build_summary)


@api_view(['GET'])
@throttle_classes([GithubThrottle])
def contributions(request):
    """Calendário de contribuições dos últimos 12 meses."""
    return respond('github:contributions', services.build_contributions)


@api_view(['GET'])
@throttle_classes([GithubThrottle])
def activity(request):
    """Últimos commits em repositórios públicos."""
    return respond('github:activity', services.build_activity)


@api_view(['GET'])
@throttle_classes([GithubThrottle])
def projects(request):
    """Repositórios em destaque, com a quantidade de commits de cada um."""
    return respond('github:projects', services.build_projects)
