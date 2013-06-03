from pyramid.config import Configurator
#from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization  import ACLAuthorizationPolicy
from pyramid.session import UnencryptedCookieSessionFactoryConfig

from .models import getAppRoot
#from .security import checkAuthentication
from .security import getGroups

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(root_factory=getAppRoot, settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)

#    authnPolicy = BasicAuthAuthenticationPolicy(check=checkAuthentication,
#                                                realm='Djosr Login') #, debug=True)
    authnPolicy = AuthTktAuthenticationPolicy(secret='sososecret',
                                              callback=getGroups) #, debug=True)
    authzPolicy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authnPolicy)
    config.set_authorization_policy(authzPolicy)

    sessFactory = UnencryptedCookieSessionFactoryConfig('itsaseekreet')
    config.set_session_factory(sessFactory)

    config.scan()
    return config.make_wsgi_app()
