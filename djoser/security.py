USERS = {'david':  '',
         'editor': 'editor',
         'viewer': 'viewer'}
GROUPS = {'editor': ['group:editors'],
          'david':  ['group:editors']}

def checkAuthentication(userid, givenPasswd, request):
    validPasswd = USERS.get(userid)
    if validPasswd is not None and validPasswd == givenPasswd:
        return GROUPS.get(userid, [])
    # Did you know?  you don't have to explicitly return None
    else:
        return None

def getGroups(userid, request):
    if userid in USERS:
        return GROUPS.get(userid, [])
