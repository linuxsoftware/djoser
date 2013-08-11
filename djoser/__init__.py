from pyramid.config import Configurator
#from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization  import ACLAuthorizationPolicy
from pyramid.session import UnencryptedCookieSessionFactoryConfig

from .app import getAppRoot
#from .users import checkAuthentication
from .users import getUser, getGroups

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(root_factory=getAppRoot, settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)

#    authnPolicy = BasicAuthAuthenticationPolicy(check=checkAuthentication,
#                                                realm='Djosr Login') #, debug=True)
    authnPolicy = AuthTktAuthenticationPolicy(secret='not telling',
                                              callback=getGroups)#, debug=True)
    authzPolicy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authnPolicy)
    config.set_authorization_policy(authzPolicy)

    sessFactory = UnencryptedCookieSessionFactoryConfig('not telling')
    config.set_session_factory(sessFactory)
    config.add_request_method(getUser, 'user', reify=True)
    config.scan()

    # this saves having to do a GET to catch simple bugs
    # TODO remove later when code is bug-free ;-)
    from pyramid.testing import DummyRequest
    dummy = DummyRequest()
    dummy.registry = config.registry
    getAppRoot(dummy)

    return config.make_wsgi_app()


